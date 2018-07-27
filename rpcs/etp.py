from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import logging
from models.coin import Coin


class Etp(Base):
    rpc_version = "2.0"
    rpc_id = 0

    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETP'
        self.tokens = settings['tokens']
        self.token_names = [x['name'] for x in self.tokens]
        logging.info("init type {}, tokens: {}".format(
            self.name, self.token_names))

    def start(self):
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[]):
        req_body = {
            'id': self.rpc_id,
            'jsonrpc': self.rpc_version,
            'method': method,
            "params": params}
        res = requests.post(
            self.settings['uri'], json.dumps(req_body), timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
            if isinstance(js, dict) and js.get('error') is not None:
                raise RpcException(js['error'])
            return js
        except ValueError as e:
            pass
        return res.text

    def is_swap_address_valid(self, did):
        res = self.make_request('getdid', [did])
        dids = res['result']
        if dids and len(dids) == 1:
            return True
        return False

    def get_balance(self, name, address):
        res = self.make_request('getaddressetp', [address])
        return res['result']['unspent']

    def get_coins(self):
        coins = []
        for x in self.tokens:
            supply = self.get_total_supply(x['name'])
            if supply != 0:
                coin = Coin()
                coin.name = self.name
                coin.token = x['name']
                coin.total_supply = supply
                coin.decimal = self.decimals(coin.token)
                coins.append(coin)
        return coins

    def get_total_supply(self, token=None):
        if token and token in self.token_names:
            res = self.make_request('getasset', [token])
            assets = res['result']
            if len(assets) > 0:
                total = sum([int(x['maximum_supply']) for x in assets])
                supply = self.from_wei(token, total)
                return supply
        return 0

    def get_account_asset(self, account, passphrase, symbol):
        res = self.make_request(
            'getaccountasset', [account, passphrase, symbol])
        assets = res['result']
        if len(assets) > 0:
            supply = int(assets[0]['quantity'])
            if symbol in self.token_names:
                supply = self.from_wei(symbol, supply)
                return supply
        return 0

    def secondary_issue(self, account, passphrase, to_did, symbol, volume):
        logging.info("secondaryissue: to_did: {}, symbol: {}, volume: {}".format(
            to_did, symbol, volume))
        tx_hash = None
        try:
            res = self.make_request(
                'secondaryissue', [account, passphrase, to_did, symbol, volume])
            result = res['result']
            if result:
                tx_hash = result['hash']
        except RpcException as e:
            logging.error("failed to secondary issue {} to {}, volume: {}, error: {}".format(
                symbol, to_did, volume, str(e)))
            raise
        return tx_hash

    def did_send_asset(self, account, passphrase, to, symbol, amount):
        tx_hash = None
        try:
            res = self.make_request(
                'didsendasset', [account, passphrase, to, symbol, amount])
            result = res['result']
            if result:
                tx_hash = result['hash']
        except RpcException as e:
            logging.error("failed to send asset to {}, symbol: {}, amount: {}, error: {}".format(
                to, symbol, amount, str(e)))
            raise
        return tx_hash

    def get_block_by_height(self, height, addresses):
        res = self.make_request('getblockheader', ['-t', int(height)])
        block_hash = res['result']['hash']
        res = self.make_request('getblock', [block_hash, 'true'])
        timestamp = res['result']['timestamp']
        transactions = res['result']['transactions']

        txs = []
        for i, trans in enumerate(transactions):
            input_addresses = [input_['address'] for input_ in trans[
                'inputs'] if input_.get('address') is not None]

            tx = {}
            for j, output in enumerate(trans['outputs']):
                to_addr = '' if output.get(
                    'address') is None else output['address']

                if output['attachment']['type'] == 'asset-transfer':
                    if to_addr not in addresses:
                        continue

                    tx['type'] = 'ETP'
                    tx['blockNumber'] = height
                    tx['index'] = i
                    tx['hash'] = trans['hash']
                    tx['to'] = to_addr
                    tx['output_index'] = j
                    tx['time'] = int(timestamp)
                    tx['input_addresses'] = input_addresses
                    tx['script'] = output['script']
                    tx['token'] = output['attachment']['symbol']
                    tx['value'] = int(output['attachment']['quantity'])

                elif output['attachment']['type'] == 'message':
                    address = output['attachment']['content'].lower()
                    if not address.startswith('0x'):
                        address = "0x{}".format(address)
                    tx['swap_address'] = address

            if tx.get('token') is not None and tx.get('swap_address') is not None:
                address = tx.get('swap_address')
                if len(address) < 42 or not self.is_hex(address[2:]):
                    logging.error("transfer {} - {}, height: {}, hash: {}, invalid swap_address: {}".format(
                        tx['token'], tx['value'], tx['hash'], tx['blockNumber'], address))
                    continue

                txs.append(tx)
                logging.info("transfer {} - {}, height: {}, hash: {}, swap_address: {}".format(
                    tx['token'], tx['value'], tx['hash'], tx['blockNumber'], address))

        res['txs'] = txs
        return res

    def is_hex(self, s):
        if s is None or s == '':
            return False
        import re
        return re.fullmatch(r"^[0-9a-f]+", s) is not None

    def is_swap(self, tx, addresses):
        if tx['type'] != self.name:
            return False
        if tx['value'] <= 0:
            return False
        if tx['token'] is None:
            return False

        if tx['token'] not in self.token_names:
            return False
        if set(tx['input_addresses']).intersection(set(addresses)):
            return False

        if tx['script'].find('numequalverify') < 0 and tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        result = None
        try:
            res = self.make_request('gettransaction', [txid])
            result = res['result']
            if result:
                result['blockNumber'] = result['height']
        except RpcException as e:
            logging.error("failed to get transaction: {}".format(str(e)))
            raise
        return result

    def new_address(self, account, passphrase):
        res = self.make_request('getnewaddress', [account, passphrase])
        addresses = res['result']
        if addresses is not None and len(addresses) > 0:
            return addresses[0]
        return None

    def get_addresses(self, account, passphrase):
        res = self.make_request('listaddresses', [account, passphrase])
        addresses = res['result']
        return addresses

    def best_block_number(self):
        res = self.make_request('getheight')
        return res['result']

    def decimals(self, token):
        for i in self.tokens:
            if i['name'] == token:
                return i['decimal']
        return 0

    def get_erc_symbol(self, token):
        return "ERC.{}".format(token)

    def before_swap(self, token, amount, total_supply, settings):
        logging.info("before_swap: token: {}, amount: {}, settings: {}".format(
            token, amount, settings))

        account = settings.get('account')
        passphrase = settings.get('passphrase')
        to_did = settings.get('did')
        symbol = self.get_erc_symbol(token)

        volume = self.get_total_supply(symbol)
        logging.info("get_total_supply: {}, {}".format(symbol, volume))

        if volume < total_supply:
            issue_volume = self.to_wei(symbol, total_supply - volume)
            tx_hash = self.secondary_issue(
                account, passphrase, to_did, symbol, issue_volume)
            return 1, tx_hash
        return 0, None

    def transfer_asset(self, to, token, amount, settings):
        logging.info("transfer_asset: to: {}, token: {}, amount: {}, settings: {}".format(
            to, token, amount, settings))

        symbol = self.get_erc_symbol(token)
        account = settings.get('account')
        passphrase = settings.get('passphrase')
        return self.did_send_asset(account, passphrase, to, symbol, amount)
