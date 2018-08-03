#!/usr/bin/env python
#! encoding=utf-8

import decimal


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

    def transfer_asset(self, to, token, amount, settings):
        pass

    def get_coins(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def get_decimal(self, token):
        return 0

    def to_wei(self, token, amount):
        dec = self.get_decimal(token)
        return int(amount * (10.0**dec))

    def from_wei(self, token, wei):
        dec = self.get_decimal(token)
        return wei * (10.0 ** (-dec))

    def before_swap(self, token, amount, issue_coin, settings):
        # 0: success, 1: need process
        return 0, None

    def after_swap(self, token, amount, settings):
        return 0, None

    def is_to_address_valid(self, address):
        return True
