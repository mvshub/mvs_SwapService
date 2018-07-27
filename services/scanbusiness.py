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

        self.swicher = {
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

    def get_tokenrpc(self, coin):
        if coin in self.swicher:
            rpc_name = self.swicher[coin]
            if rpc_name == 'ETH' and r.token != 'ERC.ETH':
                rpc_name = 'ETHToken'

            if rpc_name in self.min_confirm_map:
                return self.rpcs[rpc_name]

        return None

    @timeit
    def commit_results(self, results):
        if not results:
            for r in results:
                try:
                    # TODO
                    if not r.to:
                        b = db.session.query(Binder).filter_by(
                            binder=r.from_address).first()
                        if not b:
                            continue
                        r.to = b.to

                    rpc = self.get_tokenrpc(r.coin)
                    if not rpc:
                        continue

                    err = self.before_swap(rpc, r)
                    if err != 0:
                        continue

                    tx = rpc.transfer(self, r.coin, amount, to_, self.setting)
                    if tx:
                        r.tx_hash = tx
                        r.status = process.PROCESS_SWAP_SEND
                        result.is_confirm = process.PROCESS_UNCONFIRM
                        logging.info('success send asset:%s,tx_hash = ' %
                                     (r.token, r.tx_hash))
                        db.session.add(r)
                        db.session.commit()
                except Exception as e:
                    logging.error('process swap exception,coin,token=: %s' % (
                        r.coin, r.token, e.message))

    @timeit
    def process_confirm(self):
        results = db.session.query(Result).filter_by(
            is_confirm=process.process.PROCESS_UNCONFIRM).all()
        if not results:
            return True

        for r in results:
            if r.tx_hash == None:
                continue

            rpc = get_tokenrpc(r.coin)
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

    def before_swap(self, rpc, result):
        err = 0
        if not result.tx_hash or t.status == process.PROCESS_SWAP_NEW:
            err, tx = rpc.before_swap(r.token, r.amount, self.setting)
            if err != 0:
                result.tx_hash = tx
                result.status = process.PROCESS_SWAP_ISSUE
                result.is_confirm = process.PROCESS_UNCONFIRM
                logging.info('success issue asset:%s,tx_hash = ' %
                             (r.token, r.tx_hash))

                db.session.add(result)
                db.session.commit()

        return err

    @timeit
    def process_swap(self):
        results = db.session.query(Result).filter(
            Result.status != process.PROCESS_SWAP_FINISH)
        self.commit_results(results)

        results_new = []
        while True:
            self.swap_maxid = self.get_max_swap_id()
            swap_news = db.session.query(Swap).filter(
                Swap.iden > self.swap_maxid).limit(process.FETCH_MAX_ROW)
            if not swap_news:
                break

            for swap in swap_news:
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
                result.tx_raw = swap.tx_hash
                result.is_confirm = process.PROCESS_UNCONFIRM
                result.status = process.PROCESS_SWAP_NEW
                results_new.append(result)

            self.commit_results(results_new)

        return True

    def start(self):
        self.post(self.process_swap)
        self.post(self.process_confirm)
