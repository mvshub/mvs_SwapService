#!/usr/bin/env python
#! encoding=utf-8

from rpcs.base import Base
import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException, RpcErrorException
from utils.decimal_encoder import DecimalEncoder
from utils.exchange_rate import ExchangeRate
import json
import decimal
from models.constants import Status, TokenType, Error, SwapException
from models import constants
from models.coin import Coin
import math
import time


class Etp(Base):
    rpc_version = "2.0"
    rpc_id = 0
    blackhole_address = '1111111111111111111114oLvT2'

    def __init__(self, settings, tokens):
        Base.__init__(self, settings)

        self.token_mapping = json.loads(
            open('config/token_mapping.json').read())

        self.name = 'ETP'
        self.tokens = {}
        for token in tokens:
            name = token['name']
            token['mvs_symbol'] = self.get_mvs_symbol(name)
            self.tokens[name] = token
        self.token_names = [v['mvs_symbol'] for k, v in self.tokens.items()]

        self.etpeth_exchange_rate = 0.0

    def start(self):
        Logger.get().info("{}: tokens: {}".format(self.name, self.token_names))
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

        try:
            url = self.settings['uri']
            res = requests.post(
                url, json.dumps(req_body, cls=DecimalEncoder),
                timeout=constants.DEFAULT_REQUEST_TIMEOUT)
            if res.status_code != 200:
                raise RpcException('bad request code,%s' % res.status_code)

            js = json.loads(res.text)
            if isinstance(js, dict) and js.get('error') is not None:
                raise RpcErrorException(js['error'])
            return js
        except Exception as e:
            raise RpcErrorException(
                'Failed to make_request: {}. {}'.format(url, str(e)))
        return res.text

    def is_to_address_valid(self, did):
        dids = self.get_did(did)
        if dids and len(dids) > 0:
            return True

        if self.is_address_valid(did):
            return True

        return False

    def get_did(self, did):
        try:
            res = self.make_request('getdid', [did])
            return res['result']
        except Exception as e:
            pass
        return None

    def is_address_valid(self, address):
        if address is None or address == '':
            return False

        res = self.make_request('validateaddress', [address])
        return res['result']['is_valid']

    def get_account_asset(self, account, passphrase, token):
        if token:
            res = self.make_request(
                'getaccountasset', [account, passphrase, token])
            assets = res['result']
            if len(assets) > 0:
                total = sum([int(x['quantity']) for x in assets])
                supply = self.from_wei(token, total)
                return supply
        return 0

    def get_address_asset(self, address, token):
        if token:
            res = self.make_request(
                'getaddressasset', [address, '-s', token])
            assets = res['result']
            if len(assets) > 0:
                total = sum([int(x['quantity']) for x in assets])
                supply = self.from_wei(token, total)
                return supply
        return 0

    def get_total_supply(self, token=None):
        if token:
            res = self.make_request('getasset', [token])
            assets = res['result']
            if len(assets) > 0:
                total = sum([int(x['maximum_supply']) for x in assets])
                supply = self.from_wei(token, total)
                # burned = self.get_address_asset(blackhole_address, token)
                return supply
        return 0

    def get_balance(self, address):
        try:
            res = self.make_request('getaddressetp', [address])
            return res['result']['unspent'] * (1e-8)
        except RpcErrorException as e:
            Logger.get().error('failed to get ETP balance on address: %s, %s' % (address, str(e)))
        except Exception as e:
            raise

    def get_account_balance(self, account, passphrase):
        res = self.make_request('getbalance', [account, passphrase])
        return res['result']['total_available']

    def is_asset_exist(self, token):
        res = self.make_request('getasset', [token])
        assets = res['result']
        return len(assets) > 0

    def secondary_issue(self, account, passphrase, to_did, symbol, amount):
        tx_hash = None
        try:
            volume = self.to_wei(symbol, amount, ceil=True)
            res = self.make_request(
                'secondaryissue', [account, passphrase, to_did, symbol, volume])
            result = res['result']
            if result:
                tx_hash = result['hash']

            Logger.get().info("send_asset: to: {}, symbol: {}, amount: {}, volume: {}, tx_hash: {}".format(
                to_did, symbol, amount, volume, tx_hash))
        except RpcException as e:
            Logger.get().error("failed to secondary issue {} to {}, volume: {}, error: {}".format(
                symbol, to_did, volume, str(e)))
            raise
        return tx_hash

    def issue(self, account, passphrase, symbol):
        tx_hash = None
        try:
            res = self.make_request(
                'issue', [account, passphrase, symbol])
            result = res['result']
            if result:
                tx_hash = result['hash']

            Logger.get().info("issue symbol: {}, tx_hash: {}".format(
                symbol, tx_hash))
        except RpcException as e:
            Logger.get().error("failed to issue symbol: {}, error: {}".format(
                symbol, str(e)))
            raise
        return tx_hash

    def create_asset(self, account, passphrase, to_did, decimal, rate, symbol, amount, description):
        try:
            volume = self.to_wei(symbol, amount, ceil=True)
            res = self.make_request(
                'createasset', [account, passphrase, '-i', to_did,
                                '-n', decimal, '-r', rate, '-s', symbol, '-v', volume,
                                '-d', description])

            Logger.get().info("create_asset: to: {}, symbol: {}, amount: {}, volume: {}, deccimal: {}, rate: {}".
                              format(to_did, symbol, amount, volume, decimal, rate))
        except RpcException as e:
            Logger.get().error("failed to create_asset {} to {}, volume: {}, error: {}".format(
                symbol, to_did, volume, str(e)))
            raise

    def delete_asset(self, account, passphrase, symbol):
        try:
            res = self.make_request(
                'deletelocalasset', [account, passphrase, '-s', symbol])

            Logger.get().info("delete_asset:  symbol: {}".format(symbol))
        except RpcException as e:
            Logger.get().error("failed to delete_asset {}, error: {}".format(
                symbol, str(e)))
            raise

    def send_asset(self, account, passphrase, to, symbol, amount, fee, msg):
        tx_hash = None

        try:
            volume = self.to_wei(symbol, amount)
            fee_volume = 0  # int(volume * fee)
            params = [account, passphrase, to, symbol, volume - fee_volume]
            if msg:
                params.extend(['-i', msg])
            res = self.make_request(
                'didsendasset', params)
            result = res['result']
            if result:
                tx_hash = result['hash']

            Logger.get().info("send_asset: to: {}, symbol: {}, amount: {}, volume: {}, tx_hash: {}".format(
                to, symbol, amount, volume, tx_hash))

        except RpcException as e:
            Logger.get().error("failed to send asset to {}, symbol: {}, volume: {}, error: {}".format(
                to, symbol, volume, str(e)))
            raise
        return tx_hash, self.from_wei(symbol, fee_volume)

    def send_etp(self, account, passphrase, to, amount, swap_fee_percentage, msg):
        tx_hash = None

        try:
            volume = int(math.ceil(amount * decimal.Decimal(10.0**8)))
            swap_fee = int(volume * swap_fee_percentage / 100.0)
            volume -= swap_fee
            params = [account, passphrase]
            params.extend(['-r', "{}:{}".format(to, volume)])
            if swap_fee != 0:
                params.extend(
                    ['-r', "{}:{}".format("developer-community", swap_fee)])
            if msg:
                params.extend(['--memo', msg])
            res = self.make_request('sendmore', params)
            result = res['result']
            if result:
                tx_hash = result['hash']

            Logger.get().info("send_etp: to: {}, amount: {}, volume: {}, tx_hash: {}".format(
                to, amount, volume, tx_hash))

        except RpcException as e:
            Logger.get().error("failed to send etp to {}, volume: {}, error: {}".format(
                to, volume, str(e)))
            raise
        return tx_hash, 0

    def register_mit(self, account, passphrase, to_did, symbol, content):
        tx_hash = None

        try:
            params = [account, passphrase, to_did, symbol]
            if content:
                params.extend(['-c', content])
            res = self.make_request('registermit', params)
            result = res['result']
            if result:
                tx_hash = result['hash']

            Logger.get().info("register_mit: to: {}, symbol: {},tx_hash: {}".format(
                to_did, symbol, tx_hash))

        except RpcException as e:
            Logger.get().error("failed to register mit to: {}, symbol: {},tx_hash: {}, error: {}"
                               .format(to_did, symbol, tx_hash, str(e)))
            raise

        return tx_hash

    def send_mit(self, account, passphrase, to_did, symbol, msg=None):
        tx_hash = None
        try:
            params = [account, passphrase, to_did, symbol]
            if msg:
                params.extend(['-m', msg])
            res = self.make_request('transfermit', params)
            result = res['result']
            if result:
                tx_hash = result['hash']

            Logger.get().info("transfer_mit: to: {}, symbol: {},tx_hash: {}".format(
                to_did, symbol, tx_hash))

        except RpcException as e:
            Logger.get().error("failed to transfer mit to: {}, symbol: {},tx_hash: {}, error: {}"
                               .format(to_did, symbol, tx_hash, str(e)))
            raise

        return tx_hash, 0

    def is_invalid_to_address(self, address):
        return address is None or len(address) < 42 or not self.is_hex(address[2:])

    def is_hex(self, s):
        if s is None or s == '':
            return False
        import re
        return re.fullmatch(r"^[0-9a-f]+", s) is not None

    def get_transaction(self, txid):
        result = None
        try:
            res = self.make_request('gettransaction', [txid])
            result = res['result']
            if result:
                result['blockNumber'] = result['height']
            return result
        except RpcErrorException as e:
            Logger.get().error('failed to get tx:%s, %s' % (txid, str(e)))
        except RpcException as e:
            raise

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

    def get_decimal(self, token):
        for k, v in self.tokens.items():
            if v['mvs_symbol'] == token:
                return min(v['decimal'], constants.MAX_SWAP_ASSET_DECIMAL)
        raise SwapException(Error.EXCEPTION_CONFIG_ERROR_DECIMAL,
                            'coin={},token={}'.format(self.name, token))

    def get_fee(self, name):
        if self.tokens.get(name):
            settings = self.tokens[name]
            return settings['fee']
        return 0

    def get_mvs_symbol(self, token):
        if token in self.token_mapping:
            return self.token_mapping[token]
        elif token == 'ETH':
            return 'ETP'
        return constants.SWAP_TOKEN_PREFIX + token

    def before_swap_eth(self, token, amount, issue_coin, settings):
        account = settings.get('account')
        passphrase = settings.get('passphrase')

        self.etpeth_exchange_rate = ExchangeRate.get_etpeth_exchange_rate()
        etp_amount = amount * decimal.Decimal(self.etpeth_exchange_rate)
        volume = int(math.ceil(etp_amount * decimal.Decimal(10.0**8)))
        if volume == 0:
            raise SwapException(Error.EXCEPTION_COIN_AMOUNT_TOO_SMALL,
                                'type:eth, amount:%f' % amount)

        balances = self.get_account_balance(account, passphrase)
        if balances < volume:
            raise SwapException(Error.EXCEPTION_COIN_AMOUNT_NO_ENOUGH,
                                'available: %d, amount: %d' % (balances, volume))

        return Error.Success, None

    def get_mit_symbol(self, token, token_id):
        millis = int(round(time.time() * 1000))
        return "{}_{}_{}".format(token, token_id, millis)

    def before_swap_erc20(self, token, amount, issue_coin, settings):
        account = settings.get('account')
        passphrase = settings.get('passphrase')

        symbol = self.get_mvs_symbol(token)
        total_supply = self.get_total_supply(symbol)
        supply = self.get_account_asset(account, passphrase, symbol)
        volume = self.to_wei(symbol, amount, ceil=False)

        if volume == 0:
            raise SwapException(Error.EXCEPTION_COIN_AMOUNT_TOO_SMALL)

        if supply < amount and total_supply < issue_coin.total_supply:
            issue_amount = issue_coin.total_supply - \
                decimal.Decimal(total_supply)
            if issue_amount < decimal.Decimal(amount - supply):
                raise SwapException(Error.EXCEPTION_COIN_AMOUNT_NO_ENOUGH,
                                    'amount=%f, available=%f' % (amount, supply))

            to_did = settings.get('did')
            if not self.is_asset_exist(symbol):
                dec = self.get_decimal(symbol)
                description = "Crosschain asset of ERC20 token {}".format(
                    token)
                try:
                    self.create_asset(account, passphrase, to_did,
                                      dec, -1, symbol, issue_amount, description)
                    tx_hash = self.issue(account, passphrase, symbol)
                except RpcException as e:
                    self.delete_asset(account, passphrase, symbol)
                    raise

                return Error.Success, tx_hash
            else:
                tx_hash = self.secondary_issue(
                    account, passphrase, to_did, symbol, issue_amount)

                return Error.Success, tx_hash

        return Error.Success, None

    def before_swap_erc721(self, token, amount, issue_coin, connect, settings):
        account = settings.get('account')
        passphrase = settings.get('passphrase')
        to_did = settings.get('did')
        token_id = int(amount)
        symbol = self.get_mit_symbol(token, token_id)
        content = {
            'type': 'erc721',
            'token': token,
            'token_id': token_id,
            'hash': connect.get('hash')
        }

        connect.update(content)
        connect['mit_name'] = symbol

        return Error.Success, self.register_mit(account, passphrase, to_did, symbol, json.dumps(content))

    def before_swap(self, token, amount, issue_coin, connect, settings):
        token = result.token
        amount = result.amount
        token_type = result.token_type

        if token not in self.tokens:
            raise SwapException(Error.EXCEPTION_COIN_NOT_EXIST,
                                'coin: {}, token: {} not configed.'.format(self.name, token))

        if token_type == TokenType.Eth:
            return self.before_swap_eth(token, amount, issue_coin, settings)

        elif token_type == TokenType.Erc20:
            return self.before_swap_erc20(token, amount, issue_coin, settings)

        elif token_type == TokenType.Erc721:
            return self.before_swap_erc721(token, amount, issue_coin, connect, settings)

        else:
            raise SwapException(Error.EXCEPTION_COIN_NOT_EXIST,
                                'coin: {}, token: {}, type: {} not supported.'.format(
                                    self.name, token, token_type))

    def transfer_etp(self, to, token, amount, from_fee, msg, connect, settings):
        if self.etpeth_exchange_rate <= 0:
            raise SwapException(Error.EXCEPTION_INVAILD_EXCHANGE_RATE,
                                'etpeth_exchange_rate: %f' % self.etpeth_exchange_rate)

        account = settings.get('account')
        passphrase = settings.get('passphrase')
        etp_amount = amount * decimal.Decimal(self.etpeth_exchange_rate)
        msg['rate'] = constants.format_amount(self.etpeth_exchange_rate)
        memo = self.get_msg_memo(msg)
        swap_fee_percentage = self.get_ethetp_swap_fee_percentage(amount)
        return self.send_etp(account, passphrase, to, etp_amount, swap_fee_percentage, memo)

    def transfer_mst(self, to, token, amount, from_fee, msg, connect, settings):
        #fee = self.get_fee(token)
        msg['rate'] = constants.format_amount(msg['rate'])
        memo = self.get_msg_memo(msg)
        account = settings.get('account')
        passphrase = settings.get('passphrase')
        symbol = self.get_mvs_symbol(token)
        return self.send_asset(account, passphrase, to, symbol, amount, 0, memo)

    def transfer_mit(self, to, token, amount, from_fee, msg, connect, settings):
        account = settings.get('account')
        passphrase = settings.get('passphrase')
        symbol = connect.mit_name

        return self.send_mit(account, passphrase, to, symbol)

    def transfer_asset(self, result, msg, connect, settings):
        to = result.to_address
        token = result.token
        amount = result.amount
        from_fee = result.from_fee

        if token not in self.tokens:
            raise SwapException(Error.EXCEPTION_COIN_NOT_EXIST,
                                'coin: {}, token: {} not configed.'.format(self.name, token))

        if result.token_type == TokenType.Eth:
            return self.transfer_etp(to, token, amount, from_fee, msg, connect, settings)

        elif result.token_type == TokenType.Erc20:
            return self.transfer_mst(to, token, amount, from_fee, msg, connect, settings)

        elif result.token_type == TokenType.Erc721:
            return self.transfer_mit(to, token, amount, from_fee, msg, connect, settings)

        else:
            raise SwapException(Error.EXCEPTION_COIN_NOT_EXIST,
                                'coin: {}, token: {}, type: {} not supported.'.format(
                                    self.name, token, token_type))

    @classmethod
    def get_ethetp_swap_fee_percentage(cls, eth_amount):
        swap_fee_pecentage = 0.0
        if eth_amount < 1:
            swap_fee_pecentage = 2.0
        elif eth_amount < 5:
            swap_fee_pecentage = 2.5
        elif eth_amount < 10:
            swap_fee_pecentage = 3.0
        elif eth_amount < 15:
            swap_fee_pecentage = 3.5
        elif eth_amount <= 20:
            swap_fee_pecentage = 4.0
        else:
            raise(SwapException(Error.EXCEPTION_INVALID_SWAP_AMOUNT,
                                "at most 20 ETH can be swapped at a time, actually is {} ETH".format(eth_amount)))
        assert(swap_fee_pecentage < 100.0 and swap_fee_pecentage >= 0.0)
        return swap_fee_pecentage
