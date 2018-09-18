#!/usr/bin/env python
#! encoding=utf-8

import decimal
import math
import json
from utils.decimal_encoder import DecimalEncoder


class Base:

    def __init__(self, settings):
        self.settings = settings
        self.name = ''

    def get_transaction(self, txid):
        pass

    def get_total_supply(self, token=None):
        pass

    def best_block_number(self):
        pass

    def transfer_asset(self, result, msg, connect, settings):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def get_decimal(self, token):
        return 0

    def to_wei(self, token, amount, ceil=False):
        dec = self.get_decimal(token)
        if ceil:
            return int(math.ceil(amount * decimal.Decimal(10.0**dec)))
        else:
            return int(amount * decimal.Decimal(10.0**dec))

    def from_wei(self, token, wei):
        dec = self.get_decimal(token)
        return wei * (10.0 ** (-dec))

    def before_swap(self, token, amount, issue_coin, connect, settings):
        # 0: success, 1: need process
        return 0, None

    def after_swap(self, token, amount, settings):
        return 0, None

    def is_to_address_valid(self, address):
        return True

    @classmethod
    def get_msg_memo(cls, msg):
        key_orders = ('rate', 'amount', 'coin', 'tx_hash')
        memo = json.dumps([msg[k] for k in key_orders], cls=DecimalEncoder)
        return memo
