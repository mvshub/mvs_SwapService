#!/usr/bin/env python3

import os
import time
from tools import mailsend

def main():
    script_dir = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(script_dir + "/..")

    pwd = os.getcwd()
    prog = "main.py"

    if not os.path.exists(prog):
        print("{}/{} does not exist".format(pwd, prog))
        return False
    else:
        print("run {}/{}".format(pwd, prog))

    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    fail_count = 0
    while True:
        print("------------- {} ---------------".format(time.ctime()))
        print("check if swap service is started")

        cmd = "python3 -u {} swap".format(prog)
        found_result = os.popen("ps -ef | grep -v grep | grep '{}'".format(cmd)).read()

        if found_result == '':
            print("no, start swap service ({})".format(fail_count))
            os.system("nohup {} > /dev/null 2>&1 &".format(cmd))

            # sending mail when restart process
            if fail_count == 1 or fail_count == 2:
                subject = "MVS Swap Service Restart Warning ({})".format(fail_count)
                body = "swap service stopped ({}) and try restart at {}".format(fail_count, time.ctime())
                print("{}\n{}".format(subject, body))
                # NOTICE: call send_mail after config and testing
                #ms = mailsend.MailSending()
                #ms.send_mail("swap-service@watchdog.host", subject, body)

            fail_count += 1
        else:
            # re-count from 1, 0 stands for initial starting
            fail_count = 1
            print("yes, swap service is already started")

        print("sleep 60 seconds for next loop\n-----------\n")
        time.sleep(60)

if __name__ == '__main__':
    main()
