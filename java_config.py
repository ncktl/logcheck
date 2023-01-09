import re
from string import ascii_letters

# Logging methods of Java logging frameworks
# java.util.logging.Logger https://docs.oracle.com/javase/7/docs/api/java/util/logging/Logger.html
java_methods = "(config|entering|exiting|fine(r|st)?|info|log(p|rb)?|severe|throwing|warning)"
# For other frameworks, only the methods that don't share their name with Java Logger methods. Better to have lists -> set?
# Log4j https://logging.apache.org/log4j/2.x/log4j-api/apidocs/index.html
# Deprecated methods: entry, exit
log4j_methods = "always|catching|debug|entry|error|exit|fatal|printf|trace(Entry|Exit)?|warn"

# SLF4J https://www.slf4j.org/api/org/slf4j/Logger.html
# Has no methods that log4j doesn't have

# Logback uses SLF4J interface (?)

# Log4j and SLF4J have "fluent" logger instance methods that change the logging level and are composed with the actual
# logging methods. Keyword needs to be adapted.
# logger.atInfo().log("Hello world.");
# instead of
# logger.info("Hello world.");

keyword = re.compile(
    "(\w|\.)*log(g(ing|er))?(\.at(Debug|Error|Fatal|Info|Level\(\w*\)|Trace|Warn))?\.(config|entering|exiting|fine(r|st)?|info|log(p|rb)?|severe|throwing|warning|always|catching|debug|entry|error|exit|fatal|printf|trace(Entry|Exit)?|warn)$"
)


par_vec_onehot_expanded = []

rev_node_dict = dict()


reindex = []
