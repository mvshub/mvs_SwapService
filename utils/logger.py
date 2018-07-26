import logging
import os


def setup_logging(log_level=logging.INFO, console_or_not=False):
    fmt = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
    logging.basicConfig(level=log_level, format=fmt,
                        datefmt='%a, %d %b %Y %H:%M:%S', filename='wallet_service.log', filemode='a+')

    logging.getLogger(
        'requests.packages.urllib3.connectionpool').setLevel(logging.ERROR)

    if console_or_not:
        console = logging.StreamHandler()
        console.setLevel(log_level)
        formatter = logging.Formatter(fmt)
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
