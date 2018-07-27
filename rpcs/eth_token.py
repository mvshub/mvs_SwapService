from rpcs.eth import Eth
import decimal
import logging
from utils.exception import TransactionNotfoundException
import binascii
from models.coin import Coin

class EthToken(Eth):

    def __init__(self, settings):
        Eth.__init__(self, settings)
        self.name = settings['name']

        self.tokens = settings['tokens']
        self.token_names=[]
        self.contract_addresses=[]

        self.contract_mapaddress = settings['contract_mapaddress']

        for x in self.tokens:
            self.token_names.append(x['name'])
            self.contract_addresses.append(x['contract_address'])

        logging.info("EthToken: contract_address: {}, contract_mapaddress".format(
            self.contract_addresses, self.contract_mapaddress))

    def start(self):
        Eth.start(self)
        return True

    def stop(self):
        return False

    def get_contractaddress(self, name):
        for x in self.tokens:
            if x['name'] == name:
                return x['contract_address']
        return None

    def get_balance(self, name, address):
        contract = self.get_contractaddress(name)
        if contract is None:
            return 0
        if len(address) == 42:
            address = address[2:]
        data = '0x70a08231000000000000000000000000%s' % address
        balance = self.make_request(
            'eth_call', [{'to': contract, 'data': data}, 'latest'])
        return int(balance, 16)

    def get_coins(self):
        coins=[]
        for x in self.tokens:
            supply = self.get_total_supply(x['name'])
            if supply != 0:
                coin = Coin()
                coin.name = self.name
                coin.token = x['name']
                coin.total_supply = self.from_wei(x['name'],supply)
                coin.decimal = self.decimals(coin.token)
                coins.append(coin)
        return coins

    def get_total_supply(self, name=None):
        contract = self.get_contractaddress(name)
        if contract is None:
            return 0
        data = '0x18160ddd'
        balance = self.make_request(
            'eth_call', [{'to': contract, 'data': data}, 'latest'])
        return int(balance, 16)

    def symbol(self, name=None, contract=None):
        if contract is None:
            contract =  self.get_contractaddress(name)

        if contract is None:
            return ""

        data = '0x95d89b41'
        symbol = self.make_request(
            'eth_call', [{'to': contract, 'data': data}, 'latest'])

        if symbol is None or len(symbol) != 194:
            return ""

        strLen = int('0x' + symbol[126:130], 16)
        return str(binascii.unhexlify(symbol[130:194])[:strLen], "utf-8")

    def transfer(self, name, passphrase, from_address, to_address, amount):  # maybe failed
        contract = self.get_contractaddress(name)
        if contract is None:
            return None

        if len(to_address) == 42:
            to_address = to_address[2:]
        # self.unlock_account(from_address, passphrase)
        data = '0xa9059cbb' + ('0' * 24) + to_address + ('%064x' % amount)
        res = self.make_request('eth_sendTransaction', [
                                {'from': from_address, 'to': contract, 'data': data}])
        return res, 0

    def decimals(self, name):
        for i in self.tokens:
            if i['name'] == name:
                return int(i['decimal'])
        return 0

    def get_transaction(self, txid):
        res = self.make_request('eth_getTransactionByHash', [txid])
        if not res:
            return res

        res['blockNumber'] = int(res['blockNumber'], 16)
        input_ = res['input']
        if len(input_) != 138:
            return

        value = int('0x' + input_[74:], 16)
        to_addr = '0x' + input_[34:74]
        res['to'] = to_addr
        res['value'] = value
        receipt = self.make_request('eth_getTransactionReceipt', [txid])
        if not receipt['logs']:
            return
        return res

    def is_swap(self, tx, addresses):
        if 'type' not in tx  or tx['type'] != self.name:
            return False

        if tx['value'] <= 0:
            return False
        if tx['token'] is None or tx['token'] not in self.token_names:
            return False

        return True



    def get_block_by_height(self, height, addresses):
        block = self.make_request(
            'eth_getBlockByNumber', [hex(int(height)), True])

        block['txs']=[]
        for i, tx in enumerate(block['transactions']):
            if tx['to'] is None or tx['to'] not in (self.contract_addresses,self.contract_mapaddress):
                tx['to'] = 'create contract'
                continue

            receipt = self.make_request(
                'eth_getTransactionReceipt', [tx['hash']])
            if not receipt['logs']:
                continue

            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['time'] = int(block['timestamp'], 16)
            tx['isBinder'] = False
            tx['type'] = self.name
            input_ = tx['input']
            if tx['to'] in self.contract_addresses:
                if len(input_) != 138:
                    continue
                value = int('0x' + input_[74:], 16)
                to_addr = '0x' + input_[34:74]
                if to_addr not in addresses:
                    continue
                tx['swap_address'] = to_addr
                tx['value'] = value
                tx['amount'] = value
                tx['token'] = self.symbol(contract=tx['to'])

            else:
                if len(input_) != 202:
                    continue
                strLen = int('0x' + input_[134:138], 16)
                tx['to'] = str(binascii.unhexlify(input_[138:202])[:strLen], "utf-8")

                tx['isBinder'] = True
                logging.info('new binder found, from:%s, to:%s' % (tx['from'], tx['to']))

            block['txs'].append(tx)

        return block
