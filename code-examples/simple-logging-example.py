import logging

logging.basicConfig(filename="py-ex.log", filemode="w", level=logging.DEBUG)

def foo():
	pass

def bar():
	pass

# Logging only in except, no finally
try:
	foo()
	#unknownfunction()
except Exception as Argument:
	foo()
	logging.exception("Hello World")

# Logging only in except
try:
	foo()
	#unknownfunction()
except Exception as Argument:
	foo()
	logging.exception("Hello World")
finally:
	bar()

# Logging only in finally
try:
	foo()
except Exception as errormsg:
	foo()
finally:
	bar()
	logging.info("Test")

# No logging
try:
	foo()
except:
	bar()
finally:
	pass

# Nested logging in except, no finally
try:
	foo()
except Exception as errormsg:
	bar()
	if True:
		logging.exception("Nested logging")