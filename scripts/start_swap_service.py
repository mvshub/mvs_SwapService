#!/usr/bin/env python3

import os
import time

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

    while True:
        print("------------- {} ---------------".format(time.ctime()))
        print("check if swap service is started")

        cmd = "python3 -u {} swap".format(prog)
        found_result = os.popen("ps -ef | grep -v grep | grep '{}'".format(cmd)).read()

        if found_result == '':
            print("no, start swap service")
            os.system("nohup {} > /dev/null 2>&1 &".format(cmd))
        else:
            print("yes, swap service is already started")

        print("sleep 60 seconds for next loop\n-----------\n")
        time.sleep(60)

if __name__ == '__main__':
    main()
