import logging
import sys

logging.basicConfig(filename=__file__ + ".log", filemode="w", level=logging.DEBUG)


def foo():
    #logging.info("Hi")
    a = 5
    logging.info("Ah")
    if a == 5:
        logging.info("Five")
        a
        pass
        assert 1 == 1
    elif a == 6:
        logging.error("Hi")
    else:
        logging.info("Hey")
    try:
        b = a / 0
    except ZeroDivisionError as e:
        logging.error(e)
        sys.exit()
    else:
        logging.info("Hey")
    finally:
        logging.info("Hey")
    logging.info("Hey")


foo()