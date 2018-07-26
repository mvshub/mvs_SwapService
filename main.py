from utils.logger import setup_logging
from services.service import SwapService
import json
import signal
import logging


def main():
    setup_logging(console_or_not=True)
    settings = json.loads(open('config/service.json').read())
    service = SwapService(settings)

    def stop_signal(a, b):
        logging.info('receive signal,%s,%s' % (a, b))
        service.stop()
    signal.signal(signal.SIGINT, stop_signal)
    try:
        service.start()
    except Exception as e:
        logging.error('failed to start service,%s' % e)
        import traceback
        tb = traceback.format_exc()
        logging.error('%s', tb)

    service.stop()
    logging.info('end...')
    # service.stop()


if __name__ == '__main__':
    main()
