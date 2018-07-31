import traceback
from utils.log.logger import Logger

def trace():
    for line in traceback.format_stack():
        Logger.get().(line.strip())
