from utils.log.logger import Logger
from services.service import SwapService
import json
import signal


def main():
    settings = json.loads(open('config/service.json').read())
    service = SwapService(settings)

    def stop_signal(a, b):
        Logger.info('receive signal, %s, %s' % (a, b))
        service.stop()

    signal.signal(signal.SIGINT, stop_signal)

    try:
        service.start()
    except Exception as e:
        Logger.error('failed to start service, %s' % e)
        import traceback
        Logger.error('{}'.format(traceback.format_exc()))

    service.stop()
    Logger.info('end...')


if __name__ == '__main__':
    main()
