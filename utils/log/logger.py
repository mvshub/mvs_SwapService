# *-* coding=utf-8 *-*

import os
import sys
import threading
import logging
import logging.config
import logging.handlers
from os.path import dirname, abspath

# usages:
# import:
# from utils.log.logger import Logger
#
# Logger.info("balabala")


class Logger():
    lock = threading.Lock()
    loggerInstance = None
    logFilename = "log"

    def __init__(self):
        self.ensure_log_dir(abspath("log"))

        # use config log
        # configFile = os.path.join(dirname(__file__), "logger.conf")
        # logging.config.fileConfig(configFile, disable_existing_loggers=True)

        # use dynamic file name
        filename = 'log/{}'.format(Logger.logFilename)
        filehandler = logging.handlers.TimedRotatingFileHandler(
            filename, 'D', 1, 5, None, False, False)
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s](%(filename)s:%(lineno)d, %(threadName)s, %(funcName)s): %(message)s')
        filehandler.setFormatter(formatter)

        root_log = self.get_by_name("root")
        # remove the existing file handlers
        for hdlr in root_log.handlers[:]:
            if isinstance(hdlr, logging.handlers.TimedRotatingFileHandler):
                root_log.removeHandler(hdlr)
        root_log.addHandler(filehandler)     # set the new handler

        # add console log
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_log.addHandler(stream_handler)

        root_log.setLevel(logging.DEBUG)

        # disable log in requests
        logging.getLogger('requests').setLevel(logging.ERROR)

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

    @staticmethod
    def info(text):
        try:
            Logger.get().info(text)
        except Exception as e:
            #print("Logger error:",str(e))
            pass

    @staticmethod
    def debug(text):
        try:
            Logger.get().debug(text)
        except Exception as e:
            #print("Logger error:",str(e))
            pass

    @staticmethod
    def error(text):
        try:
            Logger.get().error(text)
        except Exception as e:
            #print("Logger error:",str(e))
            pass

    @staticmethod
    def fatal(text):
        try:
            Logger.get().fatal(text)
        except Exception as e:
            #print("Logger error:",str(e))
            pass

    @staticmethod
    def critical(text):
        try:
            Logger.get().critical(text)
        except Exception as e:
            #print("Logger error:",str(e))
            pass
