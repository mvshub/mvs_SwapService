import traceback
import logging


def trace():
    for line in traceback.format_stack():
        logging.info(line.strip())
