from services.ibusiness import IBusiness
from services.abstract import AbstractService
from models import process
from models.status import Status
from models import db
from models.swap import Swap
from models.binder import Binder
from models.coin import Coin
from models.address import Address
from models.result import Result
from utils import response
from utils import notify
from utils.timeit import timeit
import threading
import time
import logging
from decimal import Decimal
from functools import partial
import models.process
from sqlalchemy.sql import func


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

        self.coin_swap_map = {
            'ETH': 'ETP',
            'ETHToken': 'ETP',
            'ETP': 'ETH'
        }

    @timeit
    def get_max_swap_id(self):
        sub = db.session.query(db.func.max(
            Result.swap_id).label('sid')).subquery()
        results = db.session.query(Result).join(
            sub, sub.c.sid == Result.swap_id).all()
        if results and len(results) > 0:
            logging.info("get_max_swap_id: {}".format(results[0]))
            return results[0]

        return 0

    def get_swap_coin(self, coin):
        swap_coin = None
        if coin in self.coin_swap_map:
            swap_coin = self.coin_swap_map[coin]
            if swap_coin == 'ETH' and r.token != 'ERC.ETH':
                swap_coin = 'ETHToken'
        return swap_coin

    def get_swap_rpc(self, coin):
        swap_coin = self.get_swap_coin(coin)
        if swap_coin and swap_coin in self.min_confirm_map:
            return self.rpcs[swap_coin]
        return None

    @timeit
    def commit_results(self, results):
        if not results:
            return

        for r in results:
            # try:
            if not r.to_address:
                b = db.session.query(Binder).filter_by(
                    binder=r.from_address).order_by(Binder.iden.desc()).one()
                if not b:
                    continue
                r.to_address = b.to

            rpc = self.get_swap_rpc(r.coin)
            if not rpc:
                continue

            err = self.before_swap(rpc, r)
            if err != 0:
                continue

            swap_coin = self.get_swap_coin(r.coin)
            swap_settings = self.get_rpc_settings(swap_coin)
            tx = rpc.transfer_asset(self, r.token, r.amount,
                                    r.to_address, swap_settings)
            if tx:
                r.tx_hash = tx
                r.status = process.PROCESS_SWAP_SEND
                r.is_confirm = process.PROCESS_UNCONFIRM
                logging.info('success send asset:%s,tx_hash = ' %
                             (r.token, r.tx_hash))
                db.session.add(r)
                db.session.commit()
            # except Exception as e:
            #     logging.error('process swap exception, coin:%s token=: %s, error:%s' % (
            #         r.coin, r.token, str(e)))

    @timeit
    def process_confirm(self):
        results = db.session.query(Result).filter_by(
            is_confirm=process.PROCESS_UNCONFIRM).all()
        if not results:
            return True

        for r in results:
            if r.tx_hash == None:
                continue

            rpc = self.get_swap_rpc(r.coin)
            if not rpc:
                continue

            try:
                block_num = rpc.best_block_number()
                minconf = self.min_confirm_map[rpc_name]
                tx = rpc.get_transaction(r.tx_hash)

                if tx != None and tx['blockNumber'] + minconf <= block_num:
                    r.is_confirm = process.process.PROCESS_CONFIRM
                    logging.info('confirm tx:%s,tx_height:%d, cur_number:%d' %
                                 (r.tx_hash, tx['blockNumber'], block_num))

                    if r.status == process.PROCESS_SWAP_SEND:
                        r.status = process.PROCESS_SWAP_FINISH

                    db.session.add(r)
            except Exception as e:
                logging.error('failed to get tx: %s,%s' % (r.tx_hash, e))

        db.session.commit()
        return True

    def get_rpc_settings(self, coin):
        found = [x for x in self.setting['services'] if x['coin'] == coin]
        if found:
            return found[0]
        return None

    def before_swap(self, swap_rpc, result):
        err = 0
        if not result.tx_hash or result.status == process.PROCESS_SWAP_NEW:
            swap_coin = self.get_swap_coin(result.coin)
            swap_settings = self.get_rpc_settings(swap_coin)
            err, tx = swap_rpc.before_swap(
                result.token, result.amount, swap_settings)
            if err != 0:
                result.tx_hash = tx
                result.status = process.PROCESS_SWAP_ISSUE
                result.is_confirm = process.PROCESS_UNCONFIRM
                logging.info('success issue asset:%s, tx_hash:%s ' % (result.token, result.tx_hash))
                db.session.add(result)
                db.session.commit()

        return err

    @timeit
    def process_swap(self):
        new_swaps = db.session.query(Swap).filter(
            Swap.iden > self.swap_maxid).order_by(Swap.iden).limit(process.FETCH_MAX_ROW)
        if not new_swaps:
            return True

        results = []
        for swap in new_swaps:
            self.swap_maxid = swap.iden

            r = db.session.query(Result).filter_by(
                swap_id=swap.iden).first()
            if r:
                continue

            result = Result()
            result.swap_id = swap.iden
            result.from_address = swap.to_address
            result.amount = swap.amount
            result.coin = swap.coin
            result.token = swap.token
            result.tx_raw = swap.tx_hash
            result.is_confirm = process.PROCESS_UNCONFIRM
            result.status = process.PROCESS_SWAP_NEW
            results.append(result)

        self.commit_results(results)

        return True

    def process_max_swap_id(self):
        self.swap_maxid = self.get_max_swap_id()
        return False

    def start(self):
        self.post(self.process_max_swap_id)
        self.post(self.process_swap)
        self.post(self.process_confirm)
