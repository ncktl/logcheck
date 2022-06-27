import numpy as np
from pathlib import Path
from time import perf_counter as pf
import logging

logging.basicConfig(filename="py-ex.log", filemode="w", level=logging.DEBUG)

def foo():
    return True

def bar():
    pass

loggem = logging.getLogger()

# Logging only in except, no finally
try:
    foo()
#unknownfunction()
except Exception as e:
    foo()
    logging.exception("Hello World")
    np.array([1,2])
    loggem.info("object")
    logging.info("Second logging")

# Logging only in except
try:
    foo()
#unknownfunction()
except Exception as e:
    logging.exception("Hello World")
finally:
    bar()

# Logging only in finally
try:
    foo()
except Exception as e:
    foo()
finally:
    bar()
    logging.info("Test")

# No logging
try:
    foo()
except Exception as e:
    bar()
finally:
    pass

# Nested logging in except. This is not guaranteed to be reached!
try:
    foo()
except Exception as e:
    bar()
    if foo():
        logging.exception("Nested logging")

# Nested except with logging
if True:
    try:
        foo()
    except Exception as e:
        bar()
        logging.info("Test")

# Nested except without logging
if True:
    try:
        foo()
    except Exception as e:
        bar()
    logging.info("Test")

# Double nested except without logging
if True:
    if True:
        try:
            foo()
        except Exception as e:
            bar()
        logging.info("Test")

# Nested try..except inside except block
# Throws off manual exception handling counting
try:
    foo()
except Exception as e:
    # There is no logging here,
    # would be ok if the nested logging is guaranteed to be reached
    # (i.e., not like here but e.g. in a "finally" block
    try:
        bar()
    except Exception as ee:
        logging.info("Exception within an exception")

# Logging object
logger = logging.getLogger()
try:
    foo()
except Exception as e:
    logger.info("Logger")
# A
# B
# C

if True:
    def fooba():
        pass
    logging.info("hi")