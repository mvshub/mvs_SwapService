import time
from utils.log.logger import Logger


def timeit(f):
    def wrapper(*args, **kwargs):
        t1 = time.time()
        res = f(*args, **kwargs)
        t2 = time.time()
        t = t2 - t1
        if t > 2.0:
            Logger.get().info('func(%s) costs %s' % (f.__name__, t))
        return res
    return wrapper
