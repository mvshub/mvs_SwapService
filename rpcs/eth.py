from rpcs.base import Base
import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException
import json
import decimal
import binascii
from models.coin import Coin


class Eth(Base):

    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETH' if settings.get('name') is None else settings['name']
        self.contract_mapaddress = settings['contract_mapaddress'].lower()

        if 'decimal' in settings:
            self.decimal = settings['decimal']

    def start(self):
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[]):
        data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 83}
        res = requests.post('http://%s:%s' % (self.settings['host'], self.settings[
                            'port']), json.dumps(data), headers={'Content-Type': 'application/json'}, timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            raise RpcException(
                'bad response content, failed to parse,%s' % res.text)
        if js.get('error') is not None:
            raise RpcErrorException('%s' % js['error']['message'])
        return js['result']

    def get_coins(self):
        coins = []
        supply = self.get_total_supply()
        if supply != 0:
            coin = Coin()
            coin.name = self.name
            coin.token = self.name
            coin.total_supply = supply
            coin.decimal = 18
            coins.append(coin)
        return coins

    def get_total_supply(self, token_name=None):
        res = requests.get('https://www.etherchain.org/api/supply', timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            Logger.get().error(
                'bad response content, failed to parse,%s' % res.text)
            return 0

        return self.from_wei(token_name, wei=js['value']) 

    def get_transaction(self, txid):
        try:
            res = self.make_request('eth_getTransactionByHash', [txid])
            if not res:
                return res
            res['blockNumber'] = int(res['blockNumber'], 16) if res[
                'blockNumber'] else 0
            res['to'] = '' if res.get('to') is None else res['to']
            return res
        except RpcErrorException as e:
            Logger.get().error('failed to get tx:%s, %s' % (txid, str(e)))
        except Exception as e:
            raise

    def unlock_account(self, address, passphrase, unlock_time=10):
        res = self.make_request('personal_unlockAccount', [
                                address, passphrase, unlock_time])
        return res

    def new_address(self, account, passphase):
        res = self.make_request('personal_newAccount', [passphase])
        return res

    def get_addresses(self, account, passphase):
        res = self.make_request('eth_accounts', [])
        return res

    def estimate_gas(self, options):
        res = self.make_request('eth_estimateGas', [options])
        return int(res, 16)

    def transfer(self, passphrase, from_, to_, amount):
        fee = self.settings['fee']

        fee_amount = int(fee * int(amount))

        options = {'from': from_, 'to': to_,
                   'value': hex(int(amount) - fee_amount)}
        gas = self.estimate_gas(options)
        options['gas'] = hex(gas)

        res = self.make_request('eth_sendTransaction', [options])
        # return res, gas * self.settings['gasPrice']
        return res, fee_amount

    def transfer_asset(self, to, token, amount, settings):
        address = settings["scan_address"]

        if not self.unlock_account(address, settings['passphrase']):
            #logging.info('Failed to unlock_account, address:%s, passphrase:%s' % (address, settings['passphrase']))
            return None, 0

        tx_hash, fee = self.transfer(None, address, to, self.to_wei(token, amount))

        return tx_hash, self.from_wei(token, fee)

    def best_block_number(self):
        res = self.make_request('eth_blockNumber')
        return int(res, 16)

    def new_filter(self, block_height, address):
        res = self.make_request('eth_newFilter',
                                [{'fromBlock': hex(block_height),
                                  'toBlock': hex(block_height),
                                  'address': address,
                                  'topics': []}])
        return res

    def get_filter_logs(self, f):
        res = self.make_request('eth_getFilterLogs', [f])
        return res

    def is_address_valid(self, address):
        if len(address) != 42:
            return False
        try:
            int(address, 16)
        except Exception as e:
            return False
        return True

    def get_decimal(self, token):
        return 18
