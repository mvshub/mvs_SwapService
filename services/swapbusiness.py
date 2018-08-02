from services.ibusiness import IBusiness
from services.abstract import AbstractService
from models import constants
from models import db
from models.swap import Swap
from models.binder import Binder
from models.coin import Coin
from models.result import Result
from models.constants import Status, Error, SwapException
from utils import response
from utils.log.logger import Logger
from utils.timeit import timeit
import threading
import time
import traceback
from decimal import Decimal
from functools import partial
from sqlalchemy.sql import func


class SwapBusiness(IBusiness):

    def __init__(self, service_, rpcmanager_, settings):
        IBusiness.__init__(self, service=service_, rpc=None, setting=settings)
        self.rpcs = {}
        self.min_confirm_map = {}
        self.enabled_coins = []
        self.rpcmanager = rpcmanager_

        for s in self.setting['services']:
            coin = s['coin']
            self.rpcs[coin] = self.rpcmanager.get_available_feed(s['rpc'])
            self.min_confirm_map[coin] = s['minconf']
            if s['enable']:
                self.enabled_coins.append(coin)

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
            Logger.get().info("get_max_swap_id: {}".format(results[0].iden))
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

        err = Error.Success

        for r in results:
            try:

                if not r.to_address:
                    b = db.session.query(Binder).filter_by(
                        binder=r.from_address).order_by(Binder.iden.desc()).all()
                    if not b or len(b) == 0:
                        raise SwapException(Error.EXCEPTION_GET_BINDER)
                    r.to_address = b[0].to

                rpc = self.get_swap_rpc(r)
                if not rpc:
                    raise SwapException(Error.EXCEPTION_GET_COINRPC)

                self.before_swap(rpc, r)
                self.send_swap_tx(rpc, r)

            except SwapException as e:
                if e.errcode != Error.EXCEPTION_COIN_ISSUING:
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
                r.date = int(time.strftime('%4Y%2m%2d', time.localtime()))
                r.time = int(time.strftime('%2H%2M%2S', time.localtime()))
                db.session.add(r)
                db.session.commit()

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

                if tx != None and tx['blockNumber'] != 0 and tx['blockNumber'] + minconf <= block_num:
                    r.confirm_status = int(Status.Tx_Confirm)
                    Logger.get().info('confirm tx: %s, tx_height: %d, cur_number: %d' %
                                      (r.tx_hash, tx['blockNumber'], block_num))

                    if r.status == int(Status.Swap_Issue):
                        issue_coin = db.session.query(Coin).filter_by(
                            name=r.coin, token=r.token).first()
                        issue_coin.status = int(Status.Token_Normal)
                        db.session.add(issue_coin)
                        db.session.commit()
                        r.message = "confirm issued tx success"

                    elif r.status == int(Status.Swap_Send):
                        r.status = int(Status.Swap_Finish)
                        r.tx_height = tx['blockNumber']
                        r.confirm_height = block_num
                        r.date = int(time.strftime(
                            '%4Y%2m%2d', time.localtime()))
                        r.time = int(time.strftime(
                            '%2H%2M%2S', time.localtime()))
                        r.message = "confirm send tx success, swap finish"
                        Logger.get().info('finish swap, coin:%s, token=%s, swap_id:%s, tx_from:%s, from:%s, to:%s' %
                                          (r.coin, r.token, r.swap_id, r.tx_from, r.from_address, r.to_address))

                    db.session.add(r)
            except Exception as e:
                Logger.get().error('failed to get tx: %s,%s' % (r.tx_hash, e))
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
            tx, fee = rpc.transfer_asset(
                result.to_address, result.token, result.amount, swap_settings)
            if tx:
                result.tx_hash = tx
                result.status = int(Status.Swap_Send)
                result.confirm_status = int(Status.Tx_Unconfirm)
                result.fee = int(fee * 10000)
                db.message = "send tx success, wait for confirm"
                db.session.add(result)
                db.session.commit()

                Logger.get().info('success send asset: {}, {}, to: {}, tx_hash = {}'.format(
                    result.token, result.amount, result.to_address, result.tx_hash))

        return Error.Success

    def before_swap(self, swap_rpc, result):
        err = Error.Success
        if not result.tx_hash or result.status == int(Status.Swap_New):
            if not swap_rpc.is_to_address_valid(result.to_address):
                raise SwapException(Error.EXCEPTION_INVAILD_ADDRESS)

            swap_coin = self.get_swap_coin(result)
            swap_settings = self.get_rpc_settings(swap_coin)
            total_supply = 0
            issue_coin = db.session.query(Coin).filter_by(
                name=result.coin, token=result.token).order_by(Coin.iden.desc()).first()

            if not issue_coin:
                Logger.get().error("coin:%s, token %s not exist in the db" %
                                   (result.coin, result.token))
                raise SwapException(Error.EXCEPTION_COIN_NOT_EXIST)

            if issue_coin.status == int(Status.Token_Issue):
                # Logger.get().info("coin:%s, token %s is issuing" %
                #             (result.coin, result.token))
                raise SwapException(Error.EXCEPTION_COIN_ISSUING)

            total_supply = issue_coin.total_supply

            err, tx = swap_rpc.before_swap(
                result.token, result.amount, total_supply, swap_settings)
            if err == Error.Success and tx is not None:
                result.tx_hash = tx
                result.status = int(Status.Swap_Issue)
                result.confirm_status = int(Status.Tx_Unconfirm)

                issue_coin.status = int(Status.Token_Issue)
                db.message = "send issue tx success, wait for confirm"
                db.session.add(issue_coin)
                db.session.commit()
                Logger.get().info('success issue asset:%s, tx_hash:%s ' %
                                  (result.token, result.tx_hash))

        return err

    @timeit
    def process_unconfirm(self):
        results = db.session.query(Result).filter(
            Result.status != int(Status.Swap_Finish)).all()
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

            r = db.session.query(Result).filter_by(
                swap_id=swap.iden).first()
            if r:
                continue

            if swap.coin not in self.enabled_coins:
                continue

            result = Result()
            result.swap_id = swap.iden
            result.from_address = swap.from_address
            result.to_address = swap.to_address
            result.amount = Decimal(swap.amount).quantize(Decimal('0'))
            result.coin = swap.coin
            result.token = swap.token
            result.tx_from = swap.tx_hash
            result.confirm_status = int(Status.Tx_Unconfirm)
            result.status = int(Status.Swap_New)
            result.date = int(time.strftime('%4Y%2m%2d', time.localtime()))
            result.time = int(time.strftime('%2H%2M%2S', time.localtime()))
            if not result.to_address:
                b = db.session.query(Binder).filter_by(
                    binder=result.from_address).order_by(Binder.iden.desc()).all()
                if b and len(b) > 0:
                    result.to_address = b[0].to

            db.session.add(result)
            db.session.commit()

            results.append(result)

            Logger.get().info('scan swap, coin:%s, token:%s, swap_id:%s, tx_from:%s, from:%s, to:%s' %
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