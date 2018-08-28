#!/usr/bin/env python3
# coding:utf-8

import time
import json
from tools import mailsend
from multiprocessing import Process

import sys
sys.path.append('./')
sys.path.append('../')
from rpcs import etp, eth
from utils.log.logger import Logger
from utils.exception import RpcException, RpcErrorException, CriticalException

service_settings = json.loads(open('../config/service.json').read())

class BalanceMonitor:
    def __init__(self, setting):
        self.coin = setting['coin']
        self.balance_limit = setting['limit']
        self.balance = 0
        self.rpc = None
        self.address = ''

        self.parse_service_settings()
        if self.rpc == None:
            raise CriticalException("no uri/host/port is configed")
        if self.address == '':
            raise CriticalException("no did/address is configed")

    def monitor(self):
        send_flag = True
        while True:
            self.get_balance()
            if self.balance < self.balance_limit:
                if send_flag:
                    self.send_mail()
                    send_flag = False
                Logger.get().info("\n{}: Only {} balance left on account/address '{}', at time {}\n".format(self.coin, self.balance, self.address, time.ctime()))
            else:
                send_flag = True
                Logger.get().info("\n{}: Enough {} balance left on account/address '{}', at time {}".format(self.coin, self.balance, self.address, time.ctime()))
            time.sleep(60)

    def send_mail(self):
        subject = "{} Balance Monitor Warning".format(self.coin)
        body = "{}: Only {} balance left on account/address '{}', at time {}".format(
            self.coin, self.balance, self.address, time.ctime())
        Logger.get().warning("\n-------\n{}\n{}\n-------".format(subject, body))
        # NOTICE: call send_mail after config and testing
        #ms = mailsend.MailSending()
        #ms.send_mail("BalanceMonitor", subject, body)

    def get_balance(self):
        if not hasattr(self.rpc,'get_balance'):
            raise NotImplementedError("{} not supported".format(self.coin))

        while True:
            try:
                self.balance = self.rpc.get_balance(self.address)
            except Exception as e:
                print('failed to get {} balance on address: {}, {}'.format(self.coin, self.address, str(e)))
                time.sleep(5)
            else:
                break

    def parse_service_settings(self):
        coin = self.coin.lower()
        for s in service_settings['rpcs']:
            if 'name' in s and s['name'].lower() == coin:
                if coin == 'etp':
                    self.rpc = etp.Etp(s)
                elif coin == 'eth' or coin == 'ethtoken':
                    self.rpc = eth.Eth(s)

        if self.rpc == None:
            return

        did = ""
        for s in service_settings['scans']['services']:
            if s['coin'].lower() == coin:
                if 'scan_address' in s:
                    self.address = s['scan_address']
                elif 'did' in s:
                    did = s['did']

        if did != '' and coin == 'etp':
            while True:
                try:
                    res = self.rpc.make_request("getdid", [did])
                except RpcErrorException as e:
                    print('failed to get {} address of DID: {}, {}'.format(self.coin, did, str(e)))
                    break
                except Exception as e:
                    print('failed to get {} address of DID: {}, {}'.format(self.coin, did, str(e)))
                    time.sleep(5)
                else:
                    self.address = res['result'][0]['address']
                    break


if __name__ == '__main__':
    monitor_settings = (
        {'coin':'ETP', 'limit':1},
        {'coin':'ETHToken', 'limit':1},
    )

    processes = []
    for setting in monitor_settings:
        monitor = BalanceMonitor(setting)
        p = Process(target=monitor.monitor)
        processes.append(p)
        p.start()

    for p in processes:
        p.join()
