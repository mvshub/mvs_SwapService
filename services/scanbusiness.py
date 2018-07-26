from services.ibusiness import IBusiness
from services.abstract import AbstractService
from modles import process
from modles.status import Status
from modles import db
from modles.swap import Swap
from modles.binder import Binder
from modles.coin import Coin
from modles.address import Address
from modles.result import Result
from utils import response
from utils import notify
from utils.timeit import timeit
import threading
import time
import logging
from decimal import Decimal
from functools import partial
import modles.process


class ScanBusiness(IBusiness):

    def __init__(self, service_, rpcmanager_, settings):
        IBusiness.__init__(self, service=service_, rpc=None, setting=settings)
        self.rpcs = {}
        self.min_confirm_map = {}
        self.rpcmanager = rpcmanager_

        for s in self.setting['services']:
            if s['enable']:
                coin = s['coin']
                self.rpcs[coin] = self.rpcmanager.get_available_feed(s['rpc'])
                self.min_confirm_map[coin] = s['minconf']

        self.swicher = {
            'ETH': 'ETP',
            'ETHToken': 'ETP',
            'ETP': 'ETH'
        }

    @timeit
    def process_scan(self):
        results = db.session.query(Result).filter_by(
            is_confirm=process.PROCESS_UNCONFIRM).all()
        if not results:
            return True

        for r in results:
            if r.tx_hash == None or r.coin not in self.swicher:
                continue

            rpc_name = self.swicher[r.coin]
            if rpc_name == 'ETH' and r.token != 'ERC.ETH':
                rpc_name = 'ETHToken'

            if rpc_name not in self.min_confirm_map:
                continue

            rpc = self.rpcs[rpc_name]
            block_num = rpc.best_block_number()
            minconf = self.min_confirm_map[rpc_name]
            tx = rpc.get_transaction(r.tx_hash)

            if tx != None and tx['blockNumber'] + minconf <= block_num:
                r.is_confirm = process.PROCESS_CONFIRM
                logging.info('confirm tx:%s, tx_height:%d, cur_number:%d' %
                             (r.tx_hash, tx['blockNumber'], block_num))
                db.session.add(r)

        db.session.commit()

        return True

    def start(self):
        self.post(self.process_scan)
