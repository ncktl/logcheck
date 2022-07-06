import logging
import sys

logging.basicConfig(filename=__file__ + ".log", filemode="w", level=logging.DEBUG)


def foo():
    #logging.info("Hi")
    a = 5
    if a == 5:
        logging.info("Five")
    elif a == 6:
        logging.error("Hi")
    else:
        logging.info("Hey")
    try:
        b = a / 0
    except ZeroDivisionError as e:
        logging.error(e)
        sys.exit()
    logging.info("Hey")


foo()