# *-* coding=utf-8 *-*

import os
import threading
import logging
import logging.config
import logging.handlers
from os.path import dirname, abspath

# usages:
# import:
# from utils.log.logger import Logger
#
# Logger.get().info("balabala")


class Logger():
    lock = threading.Lock()
    loggerInstance = None

    def __init__(self):
        self.ensure_log_dir(abspath("log"))

        configFile = os.path.join(dirname(__file__), "logger.conf")
        logging.config.fileConfig(configFile, disable_existing_loggers=True)

        # logging.getLogger('requests').setLevel(logging.ERROR)

    def ensure_log_dir(self, logDir):
        if not os.path.exists(logDir):
            os.makedirs(logDir)

    def get_by_name(self, name):
        return logging.getLogger(name)

    @staticmethod
    def get():
        if not Logger.loggerInstance:
            with Logger.lock:
                if not Logger.loggerInstance:
                    log = Logger()
                    Logger.loggerInstance = log.get_by_name("root")
        return Logger.loggerInstance
