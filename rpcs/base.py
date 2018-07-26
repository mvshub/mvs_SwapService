import decimal

class Base:
    def __init__(self, settings):
        self.settings = settings
        self.name = ''

    def get_balance(self, name,address):
        pass

    def is_swap(self, name, tx, addresses):
        pass

    def get_transaction(self, txid):
        pass

    def total_supply(self, token_name=None):
        pass

    def best_block_number(self):
        pass

    def is_address_required(self):
        return True

    def transfer(self, name, from_, to_, amount):
        pass

    def get_coins(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def decimals(self, token):
        return 0

    def to_wei(self, token, amount):
        dec = self.decimals(token)
        return long(amount * decimal.Decimal(10.0**dec))

    def from_wei(self, token, wei):
        dec = self.decimals(token)
        return decimal.Decimal(wei) / decimal.Decimal(10.0**dec)