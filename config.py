interesting_node_types = ["if_statement", "try_statement", "function_definition"]

keyword = "logg(ing|er)"

par_vec_extended = {
    # "line": -1,
    "type": "",
    "inside_if": False,
    "inside_elif": False,
    "inside_if_else": False,
    "inside_try": False,
    "inside_except": False,
    "inside_finally": False,
    "inside_try_else": False,
    "contains_if": False,
    "contains_try": False,
    "contains_with": False,
    "contains_logging": False
}

par_vec_extended_no_type = {
    "inside_if": False,
    "inside_elif": False,
    "inside_if_else": False,
    "inside_try": False,
    "inside_except": False,
    "inside_finally": False,
    "inside_try_else": False,
    "contains_if": False,
    "contains_try": False,
    "contains_with": False,
}

par_vec_extended_debug = {
    "line": -1,
    "type": "",
    "inside_if": False,
    "inside_elif": False,
    "inside_if_else": False,
    "inside_try": False,
    "inside_except": False,
    "inside_finally": False,
    "inside_try_else": False,
    "contains_if": False,
    "contains_try": False,
    "contains_with": False,
    "contains_logging": False
}