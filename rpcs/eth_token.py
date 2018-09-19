from rpcs.eth import Eth
import json
import decimal
from utils.log.logger import Logger
from utils.exception import TransactionNotfoundException, RpcErrorException
import binascii
from models.coin import Coin
from models.constants import TokenType, SwapException, Error
from models import constants


class EthToken(Eth):

    def __init__(self, settings, tokens):
        Eth.__init__(self, settings, tokens)
        self.name = settings['name']

        self.token_mapping = json.loads(
            open('config/token_mapping.json').read())

        self.token_names = []
        self.contract_addresses = []

        self.contract_mapaddress = settings['contract_mapaddress'].lower()

        for x in self.tokens:
            self.token_names.append(x['name'])
            self.contract_addresses.append(x['contract_address'].lower())

    def start(self):
        Logger.get().info("EthToken: name:{}, contract_address: {}, contract_mapaddress: {}".format(
            self.name, self.contract_addresses, self.contract_mapaddress))
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

    def transfer(self, name, passphrase, from_address, to_address, amount, msg):
        contract = self.get_contractaddress(name)
        if contract is None:
            return None

        if len(to_address) == 42:
            to_address = to_address[2:]

        data = '0xa9059cbb' + ('0' * 24) + to_address + ('%064x' % amount)
        res = self.make_request('eth_sendTransaction', [
                                {'from': from_address, 'to': contract, 'data': data}])
        return res, 0

    def transfer2(self, name, passphrase, from_address, to_address, amount, from_fee, msg):
        contract = self.get_contractaddress(name)
        if contract is None:
            return None, 0

        #fee = self.get_fee(name)

        if to_address.startswith('0x'):
            arg_to = to_address[2:]
        else:
            arg_to = to_address

        fee_amount = 0  # int(fee * amount)
        gasPrice = self.gas_price()
        gasUsed = int(gasPrice * constants.calc_multiple(from_fee))

        data = '0xa9059cbb' + '0' * \
            (64 - len(arg_to)) + arg_to + ('%064x' % (amount - fee_amount))
        res = self.make_request('eth_sendTransaction', [
                                {'from': from_address, 'to': contract, 'data': data, 'gasPrice': hex(gasUsed)}])

        Logger.get().info("tx:%s,gasprice:%d, gasUsed:%d", res, gasPrice, gasUsed)
        return res, fee_amount

    def get_eth_token(self, symbol):
        token = None
        if symbol.startswith(constants.SWAP_TOKEN_PREFIX):
            token = symbol[len(constants.SWAP_TOKEN_PREFIX):]
        else:
            for (k, v) in self.token_mapping.items():
                if v == symbol:
                    token = k
                    break

        if not token:
            raise SwapException(
                Error.EXCEPTION_COIN_NOT_EXIST,
                '{} not start with {} or not configed.'.format(symbol, constants.SWAP_TOKEN_PREFIX))
        return token

    def transfer_asset(self, result, msg, connect, settings):
        to = result.to_address
        symbol = result.token
        amount = result.amount
        from_fee = result.from_fee
        token_type = result.token_type

        if token_type == TokenType.Erc20:
            token = self.get_eth_token(symbol)
            address = settings["scan_address"]

            if not self.unlock_account(address, settings['passphrase']):
                Logger.get().info('Failed to unlock_account, address:%s, passphrase:%s'
                                  % (address, settings['passphrase']))
                return None, 0

            memo = self.get_msg_memo(msg)
            tx_hash, fee = self.transfer2(
                token, None, address, to, self.to_wei(token, amount), from_fee, memo)
            return tx_hash, self.from_wei(token, fee)

        else:
            # TODO
            Logger.get().info("TODO token_type: {}".format(token_type))
            pass

    def get_decimal(self, name):
        for i in self.tokens:
            if i['name'] == name:
                return int(i['decimal'])
        raise SwapException(Error.EXCEPTION_CONFIG_ERROR_DECIMAL,
                            'coin=ethtoken,token=%s' % (name))

    def get_transaction(self, txid):
        try:
            res = self.make_request('eth_getTransactionByHash', [txid])
            if not res or not res['blockNumber']:
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

        except RpcErrorException as e:
            Logger.get().error('failed to get tx:%s, %s' % (txid, str(e)))
        except Exception as e:
            raise
