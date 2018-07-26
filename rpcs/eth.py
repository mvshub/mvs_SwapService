from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import logging
import binascii
from modles.coin import Coin

class Eth(Base):
    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETH' if settings.get('name') is None else settings['name']
        self.contract_mapaddress = settings['contract_mapaddress']

        if 'decimal' in settings:
            self.decimal = settings['decimal']

    def start(self):
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[]):
        data = {"jsonrpc":"2.0","method":method,"params":params,"id":83}
        res = requests.post('http://%s:%s' % (self.settings['host'], self.settings['port']), json.dumps(data), headers = {'Content-Type':'application/json'}, timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            raise RpcException('bad response content, failed to parse,%s' % res.text)
        if js.get('error') is not None:
            raise RpcException('%s' % js['error']['message'])
        # if js.get('result') is None:
        #     raise RpcException('bad response content, no result found,%s' % js)
        return js['result']

    def get_balance(self, name, address):
        res = self.make_request('eth_getBalance', [address])
        return int(res, 16)

    def get_coins(self):
        coins=[]
        supply = self.total_supply()
        if supply != 0:
            coin = Coin()
            coin.name = self.name
            coin.token = self.name
            coin.total_supply =  self.from_wei(token=None,wei=supply) 
            coin.decimal = 18
            coins.append(coin)
        return coins


    def total_supply(self, token_name=None):
        res = requests.get('https://www.etherchain.org/api/supply', timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            logging.error('bad response content, failed to parse,%s' % res.text)
            return 0
            
        return supply

    def get_block_by_height(self, height, addresses):
        
        logging.info(">>>>>>>>>> ETH : get_block_by_height")
        block = self.make_request('eth_getBlockByNumber', [hex(int(height)), True])
        block['txs'] = []
        for i, tx in enumerate(block['transactions']):
            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['time'] = int(block['timestamp'], 16)
            tx['value'] = int(tx['value'], 16)
            tx['amount'] = tx['value']
            tx['isBinder'] = False
            tx['type'] = self.name
            if tx['to'] is None :
                continue          
            elif tx['to'] == self.contract_mapaddress:
                input_ = tx['input']
                if len(input_) != 202:
                    continue
                strLen = int('0x' + input_[134:138], 16)
                tx['to'] = str(binascii.unhexlify(input_[138:202])[:strLen], "utf-8")

                tx['isBinder'] = True
                logging.info('new binder found, from:%s, to:%s' % (tx['from'], tx['to']))
            else:
                if  tx['to'] not in addresses:
                    continue
                
                tx['swap_address'] = tx['to']
                tx['token'] = 'ETH'

            block['txs'].append(tx)


        return block
    
    def is_swap(self, tx, addresses):
        if 'type' not in tx  or tx['type'] != self.name:
            return False

        if tx['value'] <= 0:
            return False
        if tx['token'] is None or tx['token'] != self.name :
            return False

        return True

    def is_deposit(self, name, tx, addresses):
        if tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        res = self.make_request('eth_getTransactionByHash', [txid])
        if not res:
            return res
        res['blockNumber'] = int(res['blockNumber'], 16) if res['blockNumber'] else 0
        res['to'] = '' if res.get('to') is None else res['to']
        return res

    def unlock_account(self, address, passphrase, unlock_time=10):
        res = self.make_request('personal_unlockAccount', [address, passphrase, unlock_time])
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
        options = {'from':from_, 'to':to_, 'value':hex(int(amount))}
        gas = self.estimate_gas(options)
        options['gas'] = gas

        # self.unlock_account(from_, passphrase)

        res = self.make_request('eth_sendTransaction', [options])
        return res, gas*self.settings['gasPrice']

    def best_block_number(self):
        res = self.make_request('eth_blockNumber')
        return int(res, 16)

    def new_filter(self, block_height, address):
        res = self.make_request('eth_newFilter', [{'fromBlock':hex(block_height),
                                              'toBlock':hex(block_height), 'address':address, 'topics':[]}])
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

    def decimals(self, token):
        return 18
