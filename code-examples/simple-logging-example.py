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

# Nested except with logging
if True:
	try:
		foo()
	except:
		bar()
		logging.info("Test")

# Nested except without logging
if True:
	try:
		foo()
	except:
		bar()
	logging.info("Test")

# Nested except without logging
if True:
	if True:
		try:
			foo()
		except:
			bar()
		logging.info("Test")

# Nested try..except inside except block
# Also throws off exception handling counting
try:
	foo()
except Exception as e:
	# There is no logging here but it not detected
	try:
		bar()
	except Exception as ee:
		logging.info("Exception within an exception")
