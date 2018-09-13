#!/usr/bin/env python3

import sys
import os
import time

sys.path.append('./')
from utils import mailer


def main():

    prog = "main.py"

    if not os.path.exists(prog):
        print("{} does not exist at current directory".format(prog))
        return False
    else:
        print("run {}/{}".format(os.getcwd(), prog))

    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    is_debug = False
    for arg in sys.argv[1:]:
        if arg == '-d' or arg == '-D':
            is_debug = True
            break
    option = '-d' if is_debug else ''

    fail_count = 0
    while True:
        print("------------- {} ---------------".format(time.ctime()))
        print("check if swap service is started")

        cmd = "python3 -u {} {} swap".format(prog, option)
        found_result = os.popen("ps -ef | grep -v grep | grep '{}'".format(cmd)).read()

        if found_result == '':
            print("no, start swap service ({})".format(fail_count))
            os.system("nohup {} > /dev/null 2>&1 &".format(cmd))

            # sending mail when restart process
            if fail_count == 1 or fail_count == 2:
                subject = "MVS Swap Service Restart Warning ({})".format(fail_count)
                body = "swap service stopped ({}) and try restart at {}".format(fail_count, time.ctime())
                print("{}\n{}".format(subject, body))
                symbol = "Swap Service Process Monitor: {}".format(sys.argv[0])
                mailer.send_mail(symbol, subject, body)

            fail_count += 1
        else:
            # re-count from 1, 0 stands for initial starting
            fail_count = 1
            print("yes, swap service is already started")

        print("sleep 60 seconds for next loop\n-----------\n")
        time.sleep(60)

if __name__ == '__main__':
    main()
