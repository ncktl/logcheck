import logging
import sys

with open("tmp.tmp", "w") as out:
    out.write("Hi")

logging.basicConfig(filename=__file__ + ".log", filemode="w", level=logging.DEBUG)

if True:
    pass

def foo(a, b):
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

try:
    pass
except:
    foo(1, logging.error("Hi"))

foo()