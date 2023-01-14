import re
from string import ascii_letters

# Logging methods of Java logging frameworks
# java.util.logging.Logger https://docs.oracle.com/javase/7/docs/api/java/util/logging/Logger.html
java_methods = [
    "config",
    "entering",
    "exiting",
    "fine",
    "finer",
    "finest",
    "info",
    "log",
    "logp",
    "logrb",
    "severe",
    "throwing",
    "warning",
]
# Log4j https://logging.apache.org/log4j/2.x/log4j-api/apidocs/index.html
# Deprecated methods: entry, exit
log4j_methods = [
    "always",
    "catching",
    "debug",
    "entry",
    "error",
    "exit",
    "fatal",
    "info",
    "log",
    "logMessage",
    "printf",
    "throwing",
    "trace",
    "traceEntry",
    "traceExit",
    "warn",
]

# SLF4J https://www.slf4j.org/api/org/slf4j/Logger.html
# Has no methods that log4j doesn't have

# Logback uses SLF4J interface (?)

# Set of all logging methods without duplicates
unified_methods = set(java_methods + log4j_methods)
# As a string for regex separated by |
unified_methods_str = "|".join(unified_methods)

# Log4j and SLF4J have "fluent" logger instance methods that change the logging level
# and are composed with the actual logging methods.
# logger.atInfo().log("Hello world.");
# logger.atLevel(INFO).log("Hello world.");
# instead of
# logger.info("Hello world.");

keyword = re.compile(
    "(\w|\.)*log(g(ing|er))?(\.at((Debug|Error|Fatal|Info|Trace|Warn)\(\)|Level\((\w|\.)+\)))?\.("
    + unified_methods_str
    + ")$"
)

# Java doesn't have compound statements.
# The following compound statements and extra clauses are those Java node types that can have a block node as a child.
compound_statements = [
    "class_body",  # class_declaration > class_body is a special block node. Can contain a block or if_statement etc.
    "compact_constructor_declaration",
    "enum_body_declarations",  # enum_declaration > enum_body > enum_body_declarations is a special block node.
    # Enums are a lot like classes. enum_body_declarations can contain a block or if_statement etc.
    "lambda_expression",  # Actual syntax: (parameter1, parameter2,..) -> { code block }
    "method_declaration",
    "static_initializer",
    "switch_rule",  # Actual syntax: case label_1, label_2, ..., label_n -> expression;|throw-statement;|block
    # Fancy new alternative to switch_block_statement_group
    # Also switch_expression > switch_block > switch_block_statement_group is a special block node
    "synchronized_statement",
    "try_statement",
    "try_with_resources_statement",

]

extra_clauses = [
    "catch_clause",
    "finally_clause",

]

par_vec_onehot_expanded = []

rev_node_dict = dict()

reindex = []
