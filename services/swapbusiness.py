from services.ibusiness import IBusiness
from services.abstract import AbstractService
from models import constants
from models import db
from models.swap import Swap
from models.binder import Binder
from models.coin import Coin
from models.result import Result
from models.constants import Status, Error, SwapException
from utils.exception import RpcException, CriticalException, RpcErrorException
from utils import response
from utils.log.logger import Logger
from utils.timeit import timeit
import threading
import time
import traceback
from decimal import Decimal
from functools import partial
from sqlalchemy.sql import func
from sqlalchemy import or_, and_, case


class SwapBusiness(IBusiness):

    def __init__(self, service_, rpcmanager_, settings):
        IBusiness.__init__(self, service=service_, rpc=None, setting=settings)
        self.rpcs = {}
        self.min_confirm_map = {}
        self.min_renew_map = {}
        self.enabled_coins = []
        self.rpcmanager = rpcmanager_

        for s in self.setting['services']:
            coin = s['coin']
            self.rpcs[coin] = self.rpcmanager.get_available_feed(s['rpc'])
            self.min_confirm_map[coin] = s['minconf']
            self.min_renew_map[coin] = s['minrenew']
            if s['enable']:
                self.enabled_coins.append(coin)

        self.coin_swap_map = {
            'ETH': 'ETP',
            'ETHToken': 'ETP',
            'ETP': 'ETHToken'
        }

        self.ban_code = (
            Error.EXCEPTION_COIN_AMOUNT_TOO_SMALL,
            Error.EXCEPTION_CONFIG_ERROR_DECIMAL,
            Error.EXCEPTION_COIN_NOT_EXIST,
            Error.EXCEPTION_INVAILD_ADDRESS
        )

    @timeit
    def get_max_swap_id(self):
        sub = db.session.query(db.func.max(
            Result.swap_id).label('sid')).subquery()
        results = db.session.query(Result).join(
            sub, sub.c.sid == Result.swap_id).all()
        if results and len(results) > 0:
            Logger.get().info("get_max_swap_id: {}".format(results[0].iden))
            return results[0].iden

        return 0

    def get_swap_coin(self, result):
        swap_coin = None
        if result.coin in self.coin_swap_map:
            swap_coin = self.coin_swap_map[result.coin]
            if swap_coin == 'ETHToken' and result.token == (constants.SWAP_TOKEN_PREFIX + 'ETH'):
                swap_coin = 'ETH'
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

        err = Error.Success

        for r in results:
            try:

                if not r.to_address:
                    b = db.session.query(Binder).filter_by(
                        binder=r.from_address).order_by(Binder.iden.desc()).all()
                    if not b or len(b) == 0:
                        raise SwapException(
                            Error.EXCEPTION_GET_BINDER, 'from_address=%s' % (r.from_address))
                    r.to_address = b[0].to

                rpc = self.get_swap_rpc(r)
                if not rpc:
                    raise SwapException(Error.EXCEPTION_GET_COINRPC)

                self.before_swap(rpc, r)
                self.send_swap_tx(rpc, r)

            except SwapException as e:
                if e.errcode != Error.EXCEPTION_COIN_ISSUING:
                    if e.errcode in self.ban_code:
                        r.status = int(Status.Swap_Ban)

                    r.message = e.get_error_str()
                    Logger.get().error('process swap exception, coin:%s, token: %s, error:%s' % (
                        r.coin, r.token, r.message))
                    Logger.get().error('{}'.format(traceback.format_exc()))

            except Exception as e:
                r.message = str(e)
                Logger.get().error('process swap exception, coin:%s, token: %s, error:%s' % (
                    r.coin, r.token, r.message))
                Logger.get().error('{}'.format(traceback.format_exc()))

            finally:
                db.session.add(r)
                db.session.commit()

    @timeit
    def process_confirm(self):
        results = db.session.query(Result).filter(and_(
            Result.confirm_status == int(Status.Tx_Unconfirm),
            Result.status != int(Status.Swap_Ban))).all()
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
                current_height = rpc.best_block_number()
                minconf = self.min_confirm_map[swap_coin]
                minRenew = self.min_renew_map[swap_coin]
                tx = rpc.get_transaction(r.tx_hash)

                tx_height_new = r.tx_height
                if tx == None:
                    if tx_height_new != 0 and tx_height_new + minRenew < current_height:
                        self.ban_swap(r, tx_height_new,
                                      current_height, minRenew)
                        # self.renew_swap(r, tx_height_new,
                        #                 current_height, minRenew)
                        continue

                if tx == None or tx['blockNumber'] == 0:
                    continue

                tx_height = int(tx['blockNumber'])

                if tx_height != r.tx_height or current_height != r.confirm_height:
                    r.tx_height = tx_height
                    r.confirm_height = current_height
                    db.session.add(r)

                if tx_height + minconf <= current_height:
                    r.confirm_status = int(Status.Tx_Confirm)
                    Logger.get().info(
                        'confirm tx: {}, tx_height: {}, cur_height: {}'.format(
                            r.tx_hash, tx_height, current_height))

                    if r.status == int(Status.Swap_Issue):
                        issue_coin = db.session.query(Coin).filter_by(
                            name=r.coin, token=r.token).first()
                        issue_coin.status = int(Status.Token_Normal)
                        db.session.add(issue_coin)
                        db.session.commit()

                        r.message = "confirm issued tx success"
                        r.date = self.get_current_date()
                        r.time = self.get_current_time()

                    elif r.status == int(Status.Swap_Send):
                        r.status = int(Status.Swap_Finish)
                        r.tx_height = tx['blockNumber']
                        r.confirm_height = current_height
                        r.date = self.get_current_date()
                        r.time = self.get_current_time()
                        r.message = "confirm send tx success, swap finish"
                        Logger.get().info(
                            'finish swap, coin: {}, token: {}, swap_id: {}, tx_from: {}, from: {}, to: {}'.format(
                                r.coin, r.token, r.swap_id, r.tx_from, r.from_address, r.to_address))

                    db.session.add(r)

            except Exception as e:
                Logger.get().error('failed to get tx: %s, error: %s' % (r.tx_hash, str(e)))
                Logger.get().error('{}'.format(traceback.format_exc()))

        db.session.commit()
        return True

    def get_rpc_settings(self, coin):
        found = [x for x in self.setting['services'] if x['coin'] == coin]
        if found:
            return found[0]
        return None

    def send_swap_tx(self, rpc, result):
        if result.status == Status.Swap_New or \
                (result.status == Status.Swap_Issue and result.confirm_status == Status.Tx_Confirm):
            swap_coin = self.get_swap_coin(result)
            swap_settings = self.get_rpc_settings(swap_coin)
            current_height = rpc.best_block_number()
            try:
                tx, fee = rpc.transfer_asset(
                    result.to_address, result.token, result.amount, result.from_fee, swap_settings)
                if tx:
                    result.tx_hash = tx
                    result.tx_height = current_height
                    result.status = int(Status.Swap_Send)
                    result.confirm_status = int(Status.Tx_Unconfirm)
                    result.fee = fee
                    db.message = "send tx success, wait for confirm"
                    result.date = self.get_current_date()
                    result.time = self.get_current_time()
                    db.session.add(result)
                    db.session.commit()

                    Logger.get().info('success send asset: token: {}, amount: {}, to: {}, tx_hash: {}'.format(
                        result.token, result.amount, result.to_address, result.tx_hash))
            except Exception as e:
                result.status = int(Status.Swap_Ban)
                result.message = str(e)
                result.date = self.get_current_date()
                result.time = self.get_current_time()
                Logger.get().info('send asset failed , forbid swap again : swap_id: {}, token: {}, amount: {}, to: {}, tx_hash: {}'.format(
                    result.swap_id, result.token, result.amount, result.to_address, result.tx_hash))
                raise

        return Error.Success

    def before_swap(self, swap_rpc, result):
        err = Error.Success
        if not result.tx_hash or result.status == int(Status.Swap_New):
            if not swap_rpc.is_to_address_valid(result.to_address):
                raise SwapException(
                    Error.EXCEPTION_INVAILD_ADDRESS, 'address=%s' % (result.to_address))

            current_height = swap_rpc.best_block_number()

            swap_coin = self.get_swap_coin(result)
            swap_settings = self.get_rpc_settings(swap_coin)
            issue_coin = db.session.query(Coin).filter_by(
                name=result.coin, token=result.token).order_by(Coin.iden.desc()).first()

            if not issue_coin:
                Logger.get().error("coin: %s, token: %s not exist in the db" %
                                   (result.coin, result.token))
                raise SwapException(Error.EXCEPTION_COIN_NOT_EXIST)

            if issue_coin.status == int(Status.Token_Issue):
                # Logger.get().info("coin:%s, token %s is issuing" %
                #             (result.coin, result.token))
                raise SwapException(Error.EXCEPTION_COIN_ISSUING)

            err, tx = swap_rpc.before_swap(
                result.token, result.amount, issue_coin, swap_settings)
            if err == Error.Success and tx is not None:
                result.tx_hash = tx
                result.tx_height = current_height
                result.status = int(Status.Swap_Issue)
                result.confirm_status = int(Status.Tx_Unconfirm)
                result.date = self.get_current_date()
                result.time = self.get_current_time()

                issue_coin.status = int(Status.Token_Issue)
                db.message = "send issue tx success, wait for confirm"
                db.session.add(issue_coin)
                db.session.commit()
                Logger.get().info('success issue asset: %s, tx_hash: %s ' %
                                  (result.token, result.tx_hash))

        return err

    @timeit
    def ban_swap(self, result, tx_height_new, current_height, minRenew)
        tx_hash = result.tx_hash
        result.status = int(Status.Swap_Ban)
        result.message = "{} maybe is reverted because it was on a forked chain.".format(
            tx_hash)
        result.date = self.get_current_date()
        result.time = self.get_current_time()
        db.session.add(result)
        Logger.get().info('ban fork swap, coin:%s, token:%s, last tx hash: %s, '
                          'last tx height: %d, cur height: %d,  ' %
                          (result.coin, result.token, tx_hash,
                           result.tx_height, current_height))

    @timeit
    def renew_swap(self, result, tx_height_new, current_height, minRenew):
        tx_hash = result.tx_hash
        tx_height = result.tx_height
        result.status = int(Status.Swap_New)
        result.confirm_status = None
        result.tx_hash = None
        result.tx_height = 0
        result.confirm_height = 0
        result.message = "renew swap"
        db.session.add(result)
        Logger.get().info('success renew swap, coin:%s, token:%s, last tx hash: %s, '
                          'last tx height: %d, cur height: %d,  ' %
                          (result.coin, result.token, tx_hash,
                           tx_height, current_height))

    @timeit
    def process_unconfirm(self):
        # only process the latest two weeks unconfirmed operations
        begin_date_to_process = int(time.strftime(
            '%4Y%2m%2d', time.localtime(time.time() - 14 * 24 * 60 * 60)))
        results = db.session.query(Result).filter(and_(
            Result.status != int(Status.Swap_Finish),
            Result.status != int(Status.Swap_Ban),
            Result.date >= begin_date_to_process)).all()
        self.commit_results(results)
        return True

    @timeit
    def process_swap(self):
        new_swaps = db.session.query(Swap).filter(
            Swap.iden > self.swap_maxid).order_by(Swap.iden).limit(constants.FETCH_MAX_ROW).all()
        if not new_swaps:
            return True

        results = []
        for swap in new_swaps:
            self.swap_maxid = swap.iden

            r = db.session.query(Result).filter(or_(
                Result.swap_id == swap.iden, Result.tx_from == swap.tx_hash)).first()
            if r:
                continue

            if swap.coin not in self.enabled_coins:
                continue

            result = Result()
            result.swap_id = swap.iden
            result.from_address = swap.from_address
            result.to_address = swap.to_address
            result.amount = Decimal(swap.amount)
            result.from_fee = Decimal(swap.fee)
            result.coin = swap.coin
            result.token = swap.token
            result.tx_from = swap.tx_hash
            result.tx_height = 0
            result.confirm_height = 0
            result.confirm_status = int(Status.Tx_Unconfirm)
            result.status = int(Status.Swap_New)
            result.date = self.get_current_date()
            result.time = self.get_current_time()
            if not result.to_address:
                b = db.session.query(Binder).filter_by(
                    binder=result.from_address).order_by(Binder.iden.desc()).all()
                if b and len(b) > 0:
                    result.to_address = b[0].to

            db.session.add(result)
            db.session.commit()

            results.append(result)

            Logger.get().info('scan swap, coin: %s, token: %s, swap_id: %s, '
                              'tx_from: %s, from: %s, to: %s' %
                              (result.coin, result.token, result.swap_id, result.tx_from,
                               ("" if not result.from_address else result.from_address),
                                  ("" if not result.to_address else result.to_address)))

        self.commit_results(results)

        return True

    def process_max_swap_id(self):
        self.swap_maxid = self.get_max_swap_id()
        return False

    def start(self):
        self.post(self.process_max_swap_id)
        self.post(self.process_unconfirm)
        self.post(self.process_swap)
        self.post(self.process_confirm)

    def get_current_date(self):
        return int(time.strftime('%4Y%2m%2d', time.localtime()))

    def get_current_time(self):
        return int(time.strftime('%2H%2M%2S', time.localtime()))
