import re
from string import ascii_letters
from dataclasses import dataclass

supported_languages = ["java", "javascript", "python"]
suf = {
    "java": ".java",
    "javascript": ".js",
    "python": ".py"
}
rev_suf = dict(zip(suf.values(), suf.keys()))


def prefix(prefix_string):
    return lambda string_list: [prefix_string + string_from_list for string_from_list in string_list]

###############################################
# Node names
###############################################
# Shared node type names
@dataclass
class NodeNames:
    error = "ERROR"
    block = "block"
    expr_stmt = "expression_statement"
    if_stmt = "if_statement"
    for_stmt = "for_statement"
    while_stmt = "while_statement"
    try_stmt = "try_statement"
    finally_clause = "finally_clause"
    return_stmt = "return_statement"
    assert_stmt = "assert_statement"
    break_stmt = "break_statement"
    continue_stmt = "continue_statement"


@dataclass
class PythonNodeNames(NodeNames):
    root = "module"
    block_types = ["block"]
    containing_block_types = ["module", "block"]
    class_def = "class_definition"
    func_def = "function_definition"
    func_call = "call"
    compound_statements = [
        class_def,
        # "decorated_definition", # Not needed: It's just the @decorator_name line
        func_def,
        NodeNames.if_stmt,
        NodeNames.for_stmt,
        "match_statement",
        NodeNames.while_stmt,
        NodeNames.try_stmt,
        "with_statement",
    ]
    extra_clauses = [
        "case_clause",
        "elif_clause",
        "else_clause",
        "except_clause",
        "except_group_clause",
        NodeNames.finally_clause
    ]
    simple_statements = [
        NodeNames.return_stmt,
        NodeNames.assert_stmt,
        NodeNames.break_stmt,
        NodeNames.continue_stmt,
        "raise_statement",
        "import_statement",
        "import_from_statement",
        "pass_statement",
        "delete_statement",
        "exec_statement",
        # "expression_statement", #  Split up
        "future_import_statement",
        "global_statement",
        "nonlocal_statement",
        "print_statement",  # Python 2 feature
    ]
    # The node types that appear inside blocks
    statements = compound_statements + simple_statements
    # A list of the statement nodes prefixed with "contains_" to be used as keys in the parameter vector dict
    contains_statements = prefix("contains_")(statements)
    expressions = [
        "assignment",
        func_call,
        "await",
        "yield"
    ]
    # A list of most python syntax node types that are visible and non-literals and also not identifiers,
    # plus module and error
    # Excludes e.g. block and expression_statement nodes
    most_node_types = [
        root,
        NodeNames.error, # Todo: Remove?
        *compound_statements,
        *extra_clauses,
        *expressions,
        *simple_statements,
        ]


@dataclass
class JavaNodeNames(NodeNames):
    root = "program"
    # Important to have "block" last, so we first go through the non-regular block types and find cases where they
    # have regular block children, which will then be processed and added to the visited nodes set
    block_types = ["constructor_body", "switch_block_statement_group", "block"]
    containing_block_types = ["program",
                              "class_body",
                              "enum_body_declarations"] + block_types
    # More types that can have statements which in turn can have blocks:
    # labeled_statement
    class_def = "class_declaration"
    func_def = "method_declaration"
    func_call = "method_invocation"
    loops = [
        NodeNames.for_stmt,
        "enhanced_for_statement",
        NodeNames.while_stmt,
        "do_statement",
    ]
    # These node types can have blocks as children or grand*children
    compound_statements = [
        *loops,
        class_def,
        func_def,  # Method declarations can only appear inside class bodies, enum bodies and interfaces
        NodeNames.if_stmt,
        NodeNames.try_stmt,
        "try_with_resources_statement",
        "switch_expression",
        "synchronized_statement"

    ]
    simple_statements = [
        NodeNames.return_stmt,
        NodeNames.assert_stmt,
        NodeNames.break_stmt,
        NodeNames.continue_stmt,
        "local_variable_declaration",
        "throw_statement", # Todo?
        "yield_statement", # Todo?
        "switch_label",
        "labeled_statement",
        "explicit_constructor_invocation",
        "record_declaration",
        "interface_declaration",
    ]
    statements = compound_statements + simple_statements  # TODO
    contains_statements = prefix("contains_")(statements)
    expressions = [
        func_call,
        "assignment_expression",
        "update_expression",
        "object_creation_expression",
        "binary_expression",
    ]
    extra_clauses = [
        "catch_clause",
        NodeNames.finally_clause,
    ]
    most_node_types = [
        root,
        NodeNames.error, # Todo: Remove?
        *statements,
        *extra_clauses,
        "else",  # artificial
        "elif",  # artificial
    ]


node_names = {
    "python": PythonNodeNames,
    "java": JavaNodeNames
}

###############################################
# Keywords
###############################################
# Old:
# python_keyword = re.compile("(\w|\.)+\.(debug|info|warning|error|critical|log|exception)$")
# New:
python_keyword = re.compile("(\w|\.)*log(g(ing|er))?\.(debug|info|warning|error|critical|log|exception)$")

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

java_keyword = re.compile(
    "(\w|\.)*log(g(ing|er))?(\.at((Debug|Error|Fatal|Info|Trace|Warn)\(\)|Level\((\w|\.)+\)))?\.("
    + unified_methods_str
    + ")$"
)

keywords = {
    "python": python_keyword,
    "java": java_keyword
}

###############################################
# Node dict: ASCII Encoding of visible node types
###############################################
python_node_dict = dict()
for i, node_type in enumerate(PythonNodeNames.most_node_types):
    python_node_dict[node_type] = ascii_letters[i]
python_rev_node_dict = dict(zip(python_node_dict.values(), python_node_dict.keys()))

java_node_dict = dict()
for i, node_type in enumerate(JavaNodeNames.most_node_types):
    java_node_dict[node_type] = ascii_letters[i]
java_rev_node_dict = dict(zip(java_node_dict.values(), java_node_dict.keys()))

node_dicts = {
    "python": python_node_dict,
    "java": java_node_dict
}
rev_node_dicts = {
    "python": python_rev_node_dict,
    "java": java_rev_node_dict
}

###############################################
# Parameter vectors for feature extraction
###############################################
def vectorize(x):
    return list(zip(x, [0] * len(x)))


agnostic_features = [
    ("type", ""),
    ("location", ""),
    ("length", 0),
    ("num_siblings", 0),
    ("num_cousins", 0),
    ("num_children", 0),
    ("depth_from_def", 0),
    ("depth_from_root", 0),
    ("parent", ""),
    ("grandparent", ""),
    ("context", "_")
]
# A list of the statement and expression nodes as well as "logging" prefixed with "contains_",
# to be used as language specific keys in the parameter vector dict (i.e. features)
python_contains = prefix("contains_")(PythonNodeNames.statements + PythonNodeNames.expressions + ["logging"])
python_parameter_vector = dict(agnostic_features + vectorize(python_contains))

# TODO: Finalize Java contains features
java_contains = prefix("contains_")(JavaNodeNames.statements + JavaNodeNames.expressions + ["logging"])
java_parameter_vector = dict(agnostic_features + vectorize(java_contains))

parameter_vectors = {
    "python": python_parameter_vector,
    "java": java_parameter_vector
}

###############################################
# Reindex
###############################################
# List of parameter vecotor keys with onehot values expanded for reindexing the parameter vector during prediction
# Assumption: num_children used; num_siblings, num_cousins, depth_from_def, depth_from_root, grandparent NOT used

python_reindex = ['length', 'num_children', 'contains_class_definition',
       'contains_function_definition', 'contains_if_statement',
       'contains_for_statement', 'contains_match_statement',
       'contains_while_statement', 'contains_try_statement',
       'contains_with_statement', 'contains_return_statement',
       'contains_assert_statement', 'contains_break_statement',
       'contains_continue_statement', 'contains_raise_statement',
       'contains_import_statement', 'contains_import_from_statement',
       'contains_pass_statement', 'contains_delete_statement',
       'contains_exec_statement', 'contains_future_import_statement',
       'contains_global_statement', 'contains_nonlocal_statement',
       'contains_print_statement', 'contains_assignment', 'contains_call',
       'contains_await', 'contains_yield', 'type_case_clause',
       'type_class_definition', 'type_elif_clause', 'type_else_clause',
       'type_except_clause', 'type_except_group_clause', 'type_finally_clause',
       'type_for_statement', 'type_function_definition', 'type_if_statement',
       'type_try_statement', 'type_while_statement', 'type_with_statement',
       'parent_case_clause', 'parent_class_definition', 'parent_elif_clause',
       'parent_else_clause', 'parent_except_clause',
       'parent_except_group_clause', 'parent_finally_clause',
       'parent_for_statement', 'parent_function_definition',
       'parent_if_statement', 'parent_module', 'parent_try_statement',
       'parent_while_statement', 'parent_with_statement']

java_reindex = ['length', 'num_children', 'contains_for_statement',
       'contains_enhanced_for_statement', 'contains_while_statement',
       'contains_do_statement', 'contains_class_declaration',
       'contains_method_declaration', 'contains_if_statement',
       'contains_try_statement', 'contains_try_with_resources_statement',
       'contains_switch_expression', 'contains_synchronized_statement',
       'contains_return_statement', 'contains_assert_statement',
       'contains_break_statement', 'contains_continue_statement',
       'contains_local_variable_declaration', 'contains_throw_statement',
       'contains_yield_statement', 'contains_switch_label',
       'contains_labeled_statement',
       'contains_explicit_constructor_invocation',
       'contains_record_declaration', 'contains_interface_declaration',
       'contains_method_invocation', 'contains_assignment_expression',
       'contains_update_expression', 'contains_object_creation_expression',
       'contains_binary_expression', 'type_catch_clause', 'type_class_body',
       'type_compact_constructor_declaration', 'type_constructor_body',
       'type_do_statement', 'type_elif', 'type_else',
       'type_enhanced_for_statement', 'type_finally_clause',
       'type_for_statement', 'type_if_statement', 'type_labeled_statement',
       'type_lambda_expression', 'type_method_declaration',
       'type_switch_block_statement_group', 'type_switch_rule',
       'type_synchronized_statement', 'type_try_statement',
       'type_try_with_resources_statement', 'type_while_statement',
       'parent_block', 'parent_catch_clause', 'parent_class_body',
       'parent_class_declaration', 'parent_constructor_body',
       'parent_constructor_declaration', 'parent_do_statement', 'parent_elif',
       'parent_else', 'parent_enhanced_for_statement', 'parent_enum_body',
       'parent_finally_clause', 'parent_for_statement', 'parent_if_statement',
       'parent_interface_body', 'parent_labeled_statement',
       'parent_lambda_expression', 'parent_method_declaration',
       'parent_object_creation_expression', 'parent_switch_block',
       'parent_switch_block_statement_group', 'parent_switch_rule',
       'parent_synchronized_statement', 'parent_try_statement',
       'parent_try_with_resources_statement', 'parent_while_statement']

reindex = {
    "python": python_reindex,
    "java": java_reindex
}


if __name__ == "__main__":
    # print(PythonNodeNames.contains_statements)
    # print(python_contains)
    # print(python_node_dict)
    # print(len(PythonNodeNames.most_node_types))
    # py_node_names = PythonNodeNames()
    # print(f"Python Compound statements:\n{PythonNodeNames.compound_statements}")
    # print(py_node_names.error)
    print(java_parameter_vector)

"""
{'module': 'a',
 'ERROR': 'b',
 'class_definition': 'c',
 'function_definition': 'd',
 'if_statement': 'e',
 'for_statement': 'f',
 'match_statement': 'g',
 'while_statement': 'h',
 'try_statement': 'i',
 'with_statement': 'j',
 'elif_clause': 'k',
 'else_clause': 'l',
 'except_clause': 'm',
 'except_group_clause': 'n',
 'finally_clause': 'o',
 'case_clause': 'p',
 'assignment': 'q',
 'call': 'r',
 'await': 's',
 'yield': 't',
 'return_statement': 'u',
 'assert_statement': 'v',
 'break_statement': 'w',
 'continue_statement': 'x',
 'raise_statement': 'y',
 'import_statement': 'z',
 'import_from_statement': 'A',
 'pass_statement': 'B',
 'delete_statement': 'C',
 'exec_statement': 'D',
 'future_import_statement': 'E',
 'global_statement': 'F',
 'nonlocal_statement': 'G',
 'print_statement': 'H'}




## Old:
{'class_definition': '0',
 'for_statement': '1',
 'function_definition': '2',
 'if_statement': '3',
 'try_statement': '4',
 'while_statement': '5',
 'with_statement': '6',
 'elif_clause': '7',
 'else_clause': '8',
 'except_clause': '9',
 'finally_clause': '10',
 'assert_statement': '11',
 'break_statement': '12',
 'continue_statement': '13',
 'delete_statement': '14',
 'exec_statement': '15',
 'future_import_statement': '16',
 'global_statement': '17',
 'import_from_statement': '18',
 'import_statement': '19',
 'nonlocal_statement': '20',
 'pass_statement': '21',
 'print_statement': '22',
 'raise_statement': '23',
 'return_statement': '24',
 'assignment': '25',
 'await': '26',
 'call': '27',
 'yield': '28'}
 
 reindex = ['length', 'num_siblings', 'num_children', 'depth_from_def', 'context',
           'contains_class_definition', 'contains_function_definition',
           'contains_if_statement', 'contains_for_statement',
           'contains_match_statement', 'contains_while_statement',
           'contains_try_statement', 'contains_with_statement',
           'contains_return_statement', 'contains_assert_statement',
           'contains_break_statement', 'contains_continue_statement',
           'contains_raise_statement', 'contains_import_statement',
           'contains_import_from_statement', 'contains_pass_statement',
           'contains_delete_statement', 'contains_exec_statement',
           'contains_future_import_statement', 'contains_global_statement',
           'contains_nonlocal_statement', 'contains_print_statement',
           'contains_assignment', 'contains_call', 'contains_await',
           'contains_yield', 'type_c', 'type_d', 'type_e', 'type_f', 'type_h',
           'type_i', 'type_j', 'type_k', 'type_l', 'type_m', 'type_n', 'type_o',
           'type_p', 'parent_a', 'parent_c', 'parent_d', 'parent_e', 'parent_f',
           'parent_g', 'parent_h', 'parent_i', 'parent_j', 'parent_k', 'parent_l',
           'parent_m', 'parent_n', 'parent_o', 'parent_p']
 
"""
