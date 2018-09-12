from utils.log.logger import Logger
from services.service import MainService
import sys
import json
import signal


def main(is_debug):
    Logger.logFilename = "swap_log"

    setting_filename = 'config/service.json'
    if is_debug:
        setting_filename = 'config/service_debug.json'
    Logger.get().info("Loading config: {}".format(setting_filename))

    settings = json.loads(open(setting_filename).read())
    service = MainService(settings)

    def stop_signal(a, b):
        Logger.get().info('receive signal, %s, %s' % (a, b))
        service.stop()

    signal.signal(signal.SIGINT, stop_signal)

    try:
        service.start()
    except Exception as e:
        Logger.get().error('failed to start service, %s' % e)
        import traceback
        Logger.get().error('{}'.format(traceback.format_exc()))

    service.stop()
    Logger.get().info('end...')


if __name__ == '__main__':
    is_debug = False
    if len(sys.argv) > 1:
        if sys.argv[1] == '-d' or sys.argv[1] == '-D':
            is_debug = True
    main(is_debug)
