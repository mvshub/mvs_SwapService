from rpcs.eth import Eth
import decimal
from utils.log.logger import Logger
from utils.exception import TransactionNotfoundException
import binascii
from models.coin import Coin


class EthToken(Eth):

    def __init__(self, settings):
        Eth.__init__(self, settings)
        self.name = settings['name']

        self.tokens = settings['tokens']
        self.token_names = []
        self.contract_addresses = []

        self.contract_mapaddress = settings['contract_mapaddress'].lower()

        for x in self.tokens:
            self.token_names.append(x['name'])
            self.contract_addresses.append(x['contract_address'].lower())

        Logger.get().info("EthToken: contract_address: {}, contract_mapaddress".format(
            self.contract_addresses, self.contract_mapaddress))

    def start(self):
        Eth.start(self)
        return True

    def stop(self):
        return False

    def get_contractaddress(self, name):
        for x in self.tokens:
            if x['name'] == name:
                return x['contract_address'].lower()
        return None

    def get_fee(self, name):
        for x in self.tokens:
            if x['name'] == name:
                return x['fee']
        return 0

    def get_coins(self):
        coins = []
        for x in self.tokens:
            supply = self.get_total_supply(x['name'])
            if supply != 0:
                coin = Coin()
                coin.name = self.name
                coin.token = x['name']
                coin.total_supply =  supply
                coin.decimal = self.get_decimal(coin.token)
                coins.append(coin)
        return coins

    def get_total_supply(self, name=None):
        contract = self.get_contractaddress(name)
        if contract is None:
            return 0
        data = '0x18160ddd'
        balance = self.make_request(
            'eth_call', [{'to': contract, 'data': data}, 'latest'])
        return self.from_wei(name, int(balance, 16))

    def symbol(self, name=None, contract=None):
        if contract is None:
            contract = self.get_contractaddress(name)

        if contract is None:
            return ""

        data = '0x95d89b41'
        symbol = self.make_request(
            'eth_call', [{'to': contract, 'data': data}, 'latest'])

        if symbol is None or len(symbol) != 194:
            return ""

        strLen = int('0x' + symbol[126:130], 16)
        return str(binascii.unhexlify(symbol[130:194])[:strLen], "utf-8")

    def transfer(self, name, passphrase, from_address, to_address, amount):
        contract = self.get_contractaddress(name)
        if contract is None:
            return None

        if len(to_address) == 42:
            to_address = to_address[2:]

        data = '0xa9059cbb' + ('0' * 24) + to_address + ('%064x' % amount)
        res = self.make_request('eth_sendTransaction', [
                                {'from': from_address, 'to': contract, 'data': data}])
        return res, 0

    def transfer2(self, name, passphrase, from_address, to_address, amount):
        contract = self.get_contractaddress(name)
        if contract is None:
            return None, 0

        fee = self.get_fee(name)

        if to_address.startswith('0x'):
            arg_to = to_address[2:]
        else:
            arg_to = to_address

        fee_amount = int(fee * amount)

        data = '0xa9059cbb' + '0' * \
            (64 - len(arg_to)) + arg_to + ('%064x' % (amount - fee_amount))
        res = self.make_request('eth_sendTransaction', [
                                {'from': from_address, 'to': contract, 'data': data}])
        return res, fee

    def transfer_asset(self, to, token, amount, settings):
        if token.startswith(constants.SWAP_TOKEN_PREFIX):
            token = token[len(constants.SWAP_TOKEN_PREFIX):]

        address = settings["scan_address"]

        if not self.unlock_account(address, settings['passphrase']):
            Logger.get().info('Failed to unlock_account, address:%s, passphrase:%s'
                              % (address, settings['passphrase']))
            return None, 0

        return self.transfer2(token, None, address, to, self.to_wei(token, amount))

    def get_decimal(self, name):
        for i in self.tokens:
            if i['name'] == name:
                return int(i['decimal'])
        return 0

    def get_transaction(self, txid):
        res = self.make_request('eth_getTransactionByHash', [txid])
        if not res:
            return res

        if not res['blockNumber']:
            return

        res['blockNumber'] = int(res['blockNumber'], 16)
        input_ = res['input']
        if len(input_) != 138:
            return

        value = int('0x' + input_[74:], 16)
        to_addr = '0x' + input_[34:74]
        res['to'] = to_addr
        res['value'] = value
        receipt = self.make_request('eth_getTransactionReceipt', [txid])
        if not (receipt and receipt['logs']):
            return
        return res
