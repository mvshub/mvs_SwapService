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

    def get_coins(self):
        coins = []
        for x in self.tokens:
            supply = self.get_total_supply(x['name'])
            if supply != 0:
                coin = Coin()
                coin.name = self.name
                coin.token = x['name']
                coin.total_supply = supply
                coin.decimal = self.get_decimal(coin.token)
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

    def create_asset(self, account, passphrase, to_did, decimal, rate, symbol, amount):
        try:
            volume = self.to_wei(symbol, amount, ceil=True)
            res = self.make_request(
                'createasset', [account, passphrase, '-i', to_did,
                                '-n', decimal, '-r', rate, '-s', symbol, '-v', volume])
            result = res['result']

            Logger.get().info("create_asset: to: {}, symbol: {}, amount: {}, volume: {}, deccimal: {}, rate: {}".
                              format(to_did, symbol, amount, volume, decimal, rate))
        except RpcException as e:
            Logger.get().error("failed to create_asset {} to {}, volume: {}, error: {}".format(
                symbol, to_did, volume, str(e)))
            raise

    def send_asset(self, account, passphrase, to, symbol, amount):
        tx_hash = None
        try:
            volume = self.to_wei(symbol, amount)
            res = self.make_request(
                'didsendasset', [account, passphrase, to, symbol, volume])
            result = res['result']
            if result:
                tx_hash = result['hash']

            Logger.get().info("send_asset: to: {}, symbol: {}, amount: {}, volume: {}, tx_hash: {}".format(
                to, symbol, amount, volume, tx_hash))

        except RpcException as e:
            Logger.get().error("failed to send asset to {}, symbol: {}, volume: {}, error: {}".format(
                to, symbol, volume, str(e)))
            raise
        return tx_hash

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

    def get_decimal(self, token):
        for i in self.tokens:
            if i['name'] == token:
                return i['decimal']
        return 0

    def get_erc_symbol(self, token):
        return "ERC.{}".format(token)

    def before_swap(self, token, amount, issue_coin, settings):
        symbol = self.get_erc_symbol(token)
        supply = self.get_total_supply(symbol)

        if supply < issue_coin.total_supply:
            account = settings.get('account')
            passphrase = settings.get('passphrase')
            to_did = settings.get('did')
            issue_amount = issue_coin.total_supply - decimal.Decimal(supply)

            if not self.is_asset_exist(symbol):
                dec = self.get_decimal(symbol)
                self.create_asset(account, passphrase, to_did,
                                 dec, -1, symbol, issue_amount)
                tx_hash = self.issue(account, passphrase, symbol)
                return Error.Success, tx_hash
            else:
                tx_hash = self.secondary_issue(
                    account, passphrase, to_did, symbol, issue_amount)
                return Error.Success, tx_hash

        return Error.Success, None

    def transfer_asset(self, to, token, amount, settings):
        symbol = self.get_erc_symbol(token)
        account = settings.get('account')
        passphrase = settings.get('passphrase')
        return self.send_asset(account, passphrase, to, symbol, amount), 0
