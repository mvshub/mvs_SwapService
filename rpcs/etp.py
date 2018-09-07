#!/usr/bin/env python
#! encoding=utf-8

from rpcs.base import Base
import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException, RpcErrorException
from utils.decimal_encoder import DecimalEncoder
import json
import decimal
from models.constants import Status, Error, SwapException
from models import constants
from models.coin import Coin
import math


class Etp(Base):
    rpc_version = "2.0"
    rpc_id = 0
    blackhole_address = '1111111111111111111114oLvT2'

    def __init__(self, settings, tokens):
        Base.__init__(self, settings)

        self.erc20_tokens = json.loads(open('config/erc20_tokens.json').read())

        self.name = 'ETP'
        self.tokens = {}
        for token in tokens:
            name = token['name']
            token['mvs_symbol'] = self.get_mvs_symbol(name)
            self.tokens[name] = token
        self.token_names = [v['mvs_symbol'] for k, v in self.tokens.items()]

        self.exchange_rate = 0.0

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
        res = requests.post(
            self.settings['uri'], json.dumps(req_body, cls=DecimalEncoder), timeout=constants.DEFAULT_REQUEST_TIMEOUT)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
            if isinstance(js, dict) and js.get('error') is not None:
                raise RpcErrorException(js['error'])
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
        try:
            res = self.make_request('getdid', [did])
            return res['result']
        except Exception as e:
            pass

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

    def get_balance(self, account, passphrase):
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

            if 'result' not in res:
                raise

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

            if 'result' not in res:
                raise

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

    def send_etp(self, account, passphrase, to, amount, msg):
        tx_hash = None

        try:
            fee_volume = 0
            volume = int(math.ceil(amount * decimal.Decimal(10.0**8)))
            params = [account, passphrase, to, volume]
            if msg:
                params.extend(['-m', msg])
            res = self.make_request('send', params)
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
        if token in self.erc20_tokens:
            return self.erc20_tokens[token]
        elif token == 'ETH':
            return 'ETP'
        return constants.SWAP_TOKEN_PREFIX + token

    def before_swap(self, token, amount, issue_coin, settings):
        if token == 'ETH':
            self.exchange_rate = self.get_exchange_rate(token)
            etp_amount = amount * self.exchange_rate
            volume = int(math.ceil(etp_amount * decimal.Decimal(10.0**8)))
            if volume == 0:
                raise SwapException(Error.EXCEPTION_COIN_AMOUNT_TOO_SMALL,
                    'type:eth, amount:%f' % amount)

            account = settings.get('account')
            passphrase = settings.get('passphrase')
            balances = self.get_balance(account, passphrase)
            if balances < volume:
                raise SwapException(Error.EXCEPTION_COIN_AMOUNT_NO_ENOUGH,
                    'available: %d, amount: %d' % (balances, volume))

            return Error.Success, None

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

    def get_exchange_rate(self, token):
        rate = 88
        rate_url = None
        if self.tokens.get(token):
            settings = self.tokens[token]
            if settings.get('exchange_rate_url'):
                rate_url = settings['exchange_rate_url']

        if not rate_url:
            symbol = self.get_mvs_symbol(token)
            raise SwapException(Error.EXCEPTION_CONFIG_ERROR_EXCHANGE_RATE_URL,
                                'token: {}, target: {}' % (token, symbol))

        # TODO get rate from rate_url
        return rate

    def transfer_asset(self, to, token, amount, from_fee, msg, settings):
        if token == 'ETH':
            if self.exchange_rate <= 0:
                raise SwapException(Error.EXCEPTION_INVAILD_EXCHANGE_RATE,
                                'exchange_rate: %f' % self.exchange_rate)

            account = settings.get('account')
            passphrase = settings.get('passphrase')
            etp_amount = amount * self.exchange_rate
            msg['rate'] = self.exchange_rate
            memo = json.dumps([v for k,v in msg.items()], cls=DecimalEncoder)
            return self.send_etp(account, passphrase, to, etp_amount, memo)
        else:
            #fee = self.get_fee(token)
            symbol = self.get_mvs_symbol(token)
            account = settings.get('account')
            passphrase = settings.get('passphrase')
            memo = json.dumps([v for k,v in msg.items()], cls=DecimalEncoder)
            return self.send_asset(account, passphrase, to, symbol, amount, 0, memo)
