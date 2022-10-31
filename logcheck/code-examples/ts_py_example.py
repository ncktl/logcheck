import logging
import sys

with open("tmp.tmp", "w") as out:
    out.write("Hi")

logging.basicConfig(filename=__file__ + ".log", filemode="w", level=logging.DEBUG)

if True:
    print("Hi")


def foo(a, b):
    # logging.info("Hi")
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
    # finally:
    #     logging.info("Hey")
    logging.info("Hey")


def decorator_list(fnc):
    def inner(list_of_tuples):
        return [fnc(val[0], val[1]) for val in list_of_tuples]

    return inner


def decorator_list_foo(fnc):
    def inner(list_of_tuples):
        return [fnc(val[0], val[1]) for val in list_of_tuples]

    return inner


@decorator_list_foo
@decorator_list
def add_together(a, b):
    return a + b


for i in range(10):
    print("Hi")
    foo(1, 2)
    if True:
        print("Hi")
    elif False:
        print("Hi")

try:
    print("Hi")
finally:
    for cb_op_id in self._sync_cb_map.keys():
        self._InvokeSyncCallbacks(cb_op_id)

    # Complete execution.
    self._is_executing = False
    self._callback()

    # Test
    print("Hi")
