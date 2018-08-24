#!/usr/bin/env python
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
                Logger.get().info("\n{\n}: Only {} balance left on account/address '{}', at time {}\n".format(self.coin, self.balance, self.address, time.ctime()))
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
        coin = self.coin.lower()
        if coin == 'etp':
            self.get_etp_balance()
        elif coin == 'eth':
            self.get_eth_balance()
        else:
            raise NotImplementedError("{} not supported".format(self.coin))

    def get_etp_balance(self):
        while True:
            try:
                res = self.rpc.make_request("getaddressetp", [self.address])
                self.balance = res['result']['unspent'] * (10 ** -8)
            except RpcErrorException as e:
                print(e)
                break
            except Exception as e:
                print(e)
                time.sleep(5)
            else:
                break

    def get_eth_balance(self):
        while True:
            try:
                res = self.rpc.make_request("eth_getBalance", [self.address])
                self.balance = res * (10 ** -18)
            except RpcErrorException as e:
                print(e)
                break
            except Exception as e:
                print(e)
                time.sleep(5)
            else:
                break

    def parse_service_settings(self):
        coin = self.coin.lower()
        for s in service_settings['rpcs']:
            if 'name' in s and s['name'].lower() == coin:
                if coin == 'etp':
                    self.rpc = etp.Etp(s)
                elif coin == 'eth':
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

        if self.address != '' or did == '':
            return

        while True:
            try:
                res = self.rpc.make_request("getdid", [did])
            except RpcErrorException as e:
                print(e)
                break
            except Exception as e:
                print(e)
                time.sleep(5)
            else:
                self.address = res['result'][0]['address']
                break


if __name__ == '__main__':
    monitor_settings = (
        {'coin':'ETP', 'limit':100},
        {'coin':'ETH', 'limit':10},
    )

    processes = []
    for setting in monitor_settings:
        monitor = BalanceMonitor(setting)
        p = Process(target=monitor.monitor)
        processes.append(p)
        p.start()

    for p in processes:
        p.join()
