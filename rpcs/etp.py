#!/usr/bin/env python
#! encoding=utf-8

from rpcs.base import Base
import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException
import json
import decimal
from models.constants import Status, Error
from models.coin import Coin


class Etp(Base):
    rpc_version = "2.0"
    rpc_id = 0

    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETP'
        self.tokens = settings['tokens']
        self.token_names = [x['name'] for x in self.tokens]
        Logger.get().info("init type {}, tokens: {}".format(
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

    def is_to_address_valid(self, did):
        dids = self.get_did(did)
        if dids and len(dids) > 0:
            return True

        if self.is_address_valid(did):
            return True

        return False

    def get_did(self, did):
        res = self.make_request('getdid', [did])
        return res['result']

    def is_address_valid(self, address):
        if address is None or address == '':
            return False

        res = self.make_request('validateaddress', [address])
        return res['result']['is_valid']

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
        if token:
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
            supply = self.from_wei(symbol, supply)
            return supply
        return 0

    def secondary_issue(self, account, passphrase, to_did, symbol, volume):
        Logger.get().info("secondary_issue: to_did: {}, symbol: {}, volume: {}".format(
            to_did, symbol, volume))
        tx_hash = None
        try:
            res = self.make_request(
                'secondaryissue', [account, passphrase, to_did, symbol, volume])
            result = res['result']
            if result:
                tx_hash = result['hash']
        except RpcException as e:
            Logger.get().error("failed to secondary issue {} to {}, volume: {}, error: {}".format(
                symbol, to_did, volume, str(e)))
            raise
        return tx_hash

    def send_asset(self, account, passphrase, to, symbol, amount):
        tx_hash = None
        try:
            res = self.make_request(
                'didsendasset', [account, passphrase, to, symbol, amount])
            result = res['result']
            if result:
                tx_hash = result['hash']
        except RpcException as e:
            Logger.get().error("failed to send asset to {}, symbol: {}, amount: {}, error: {}".format(
                to, symbol, amount, str(e)))
            raise
        return tx_hash

    def get_block_by_height(self, height, addresses):
        res = self.make_request('getblock', [height])
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
                    tx['swap_address'] = to_addr
                    tx['output_index'] = j
                    tx['time'] = int(timestamp)
                    tx['input_addresses'] = input_addresses
                    tx['script'] = output['script']
                    tx['token'] = output['attachment']['symbol']
                    tx['value'] = int(output['attachment']['quantity'])
                    tx['from'] = None

                elif output['attachment']['type'] == 'message':
                    address = output['attachment']['content'].lower()
                    if not address.startswith('0x'):
                        address = "0x{}".format(address)
                    tx['to'] = address

            if tx.get('token') is not None and tx.get('to') is not None:
                address = tx.get('to')
                if self.is_invalid_to_address(address):
                    Logger.get().error("transfer {} - {}, height: {}, hash: {}, invalid to: {}".format(
                        tx['token'], tx['value'], tx['hash'], tx['blockNumber'], address))
                    continue

                txs.append(tx)
                Logger.get().info("transfer {} - {}, height: {}, hash: {}, to: {}".format(
                    tx['token'], tx['value'], tx['blockNumber'], tx['hash'], address))

        res['txs'] = txs
        return res

    def is_invalid_to_address(self, address):
        return address is None or len(address) < 42 or not self.is_hex(address[2:])

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
            Logger.get().error("failed to get transaction: {}".format(str(e)))
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

    def before_swap(self, token, amount, issue_coin, settings):
        # Logger.get().info("before_swap: token: {}, amount: {}".format(token, amount))

        symbol = self.get_erc_symbol(token)
        volume = self.get_total_supply(symbol)

        total_supply = issue_coin.total_supply
        if volume < total_supply:
            account = settings.get('account')
            passphrase = settings.get('passphrase')
            to_did = settings.get('did')
            amount = total_supply - volume
            issue_volume = int(
                amount * decimal.Decimal(10.0 ** issue_coin.decimal))

            tx_hash = self.secondary_issue(
                account, passphrase, to_did, symbol, issue_volume)
            return Error.Success, tx_hash
        return Error.Success, None

    def transfer_asset(self, to, token, amount, settings):
        symbol = self.get_erc_symbol(token)
        volume = int(decimal.Decimal(amount))

        Logger.get().info("transfer_asset: to: {}, token: {}, amount: {}".format(
            to, symbol, volume))

        account = settings.get('account')
        passphrase = settings.get('passphrase')
        return self.send_asset(account, passphrase, to, symbol, volume), 0
