interesting_node_types = ["if_statement", "try_statement", "function_definition"]

keyword = "logg(ing|er)"

par_vec_extended = {
    "line": -1,
    "if_statement": False,
    "try_statement": False,
    "function_definition": False,
    "child_of_class_definition": False,
    "child_of_decorated_definition": False,
    "child_of_elif_clause": False,
    "child_of_else_clause": False,
    "child_of_except_clause": False,
    "child_of_finally_clause": False,
    "child_of_for_statement": False,
    "child_of_function_definition": False,
    "child_of_if_statement": False,
    "child_of_module": False,
    "child_of_try_statement": False,
    "child_of_while_statement": False,
    "child_of_with_statement": False,
    "contains_if": False,
    "contains_try": False,
    "contains_with": False,
    "contains_logging": False
}
