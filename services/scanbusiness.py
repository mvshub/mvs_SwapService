from services.ibusiness import IBusiness
from services.abstract import AbstractService
from models import constants
from models import db
from models.swap import Swap
from models.binder import Binder
from models.coin import Coin
from models.result import Result
from models.constants import Status, Error
from utils import response
from utils import notify
from utils.timeit import timeit
import threading
import time
import logging
from decimal import Decimal
from functools import partial
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
            return results[0].iden

        return 0

    def get_swap_coin(self, result):
        swap_coin = None
        if result.coin in self.coin_swap_map:
            swap_coin = self.coin_swap_map[result.coin]
            if swap_coin == 'ETH' and result.token != 'ERC.ETH':
                swap_coin = 'ETHToken'
        return swap_coin

    def get_swap_rpc(self, result):
        swap_coin = self.get_swap_coin(result)
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
                    binder=r.from_address).order_by(Binder.iden.desc()).all()
                if not b:
                    continue
                r.to_address = b[0].to

            rpc = self.get_swap_rpc(r)
            if not rpc:
                continue

            err = self.before_swap(rpc, r)
            if err != 0:
                continue

            swap_coin = self.get_swap_coin(r)
            swap_settings = self.get_rpc_settings(swap_coin)
            tx = rpc.transfer_asset(
                r.to_address, r.token, r.amount, swap_settings)
            if tx:
                r.tx_hash = tx
                r.status = int(Status.Swap_Send)
                r.confirm_status = int(Status.Tx_Unconfirm)
                db.session.add(r)
                db.session.commit()

                logging.info('success send asset: {}, {}, to: {}, tx_hash = {}'.format(
                    r.token, r.amount, r.to_address, r.tx_hash))

            # except Exception as e:
            #    logging.error('process swap exception, coin:%s token=: %s, error:%s' % (
            #        r.coin, r.token, str(e)))

    @timeit
    def process_confirm(self):
        results = db.session.query(Result).filter_by(
            confirm_status=int(Status.Tx_Unconfirm)).all()
        if not results:
            return True

        for r in results:
            if r.tx_hash == None:
                continue

            rpc = self.get_swap_rpc(r)
            if not rpc:
                continue

            swap_coin = self.get_swap_coin(r)
            try:
                block_num = rpc.best_block_number()
                minconf = self.min_confirm_map[swap_coin]
                tx = rpc.get_transaction(r.tx_hash)

                if tx != None and tx['blockNumber'] + minconf <= block_num:
                    r.confirm_status = int(Status.Tx_Confirm)
                    logging.info('confirm tx:%s,tx_height:%d, cur_number:%d' %
                                 (r.tx_hash, tx['blockNumber'], block_num))

                    if r.status == int(Status.Swap_Issue):
                        issue_coin = db.session.query(Coin).filter_by(
                            name=r.coin, token=r.token)
                        issue_coin.status = int(Status.Token_Normal)
                        db.session.add(issue_coin)
                        db.session.commit()

                    elif r.status == int(Status.Swap_Send):
                        r.status = int(Status.Swap_Finish)

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
        if not result.tx_hash or result.status == int(Status.Swap_New):
            if not swap_rpc.is_swap_address_valid(result.to_address):
                return -1

            swap_coin = self.get_swap_coin(result)
            swap_settings = self.get_rpc_settings(swap_coin)
            total_supply = 0
            issue_coin = db.session.query(Coin).filter_by(
                name=result.coin, token=result.token).all()

            if not issue_coin:
                logging.info("coin:%s, token %s not exist in the db" %
                             (result.coin, result.token))
                return -1

            if issue_coin.status == int(Status.Token_Issue):
                logging.info("coin:%s, token %s is issuing" %
                             (result.coin, result.token))
                return -2

            issue_coin = issue_coin[0]
            total_supply = issue_coin.total_supply

            err, tx = swap_rpc.before_swap(
                result.token, result.amount, total_supply, swap_settings)
            if err == Error.Success and tx is not None:
                result.tx_hash = tx
                result.status = int(Status.Swap_Issue)
                result.confirm_status = int(Status.Tx_Unconfirm)

                issue_coin.status = int(Status.Token_Issue)
                db.session.add(issue_coin)

                db.session.add(result)
                db.session.commit()

                logging.info('success issue asset:%s, tx_hash:%s ' %
                             (result.token, result.tx_hash))

        return err

    @timeit
    def process_unconfirm(self):
        results = db.session.query(Result).filter(
            Result.status != int(Status.Swap_Finish))
        self.commit_results(results)
        return True

    @timeit
    def process_swap(self):
        new_swaps = db.session.query(Swap).filter(
            Swap.iden > self.swap_maxid).order_by(Swap.iden).limit(constants.FETCH_MAX_ROW)
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
            result.confirm_status = int(Status.Tx_Unconfirm)
            result.status = int(Status.Swap_New)
            results.append(result)

        self.commit_results(results)

        return True

    def process_max_swap_id(self):
        # self.swap_maxid = self.get_max_swap_id()
        self.swap_maxid = 0
        return False

    def start(self):
        self.post(self.process_max_swap_id)
        self.post(self.process_unconfirm)
        self.post(self.process_swap)
        self.post(self.process_confirm)
