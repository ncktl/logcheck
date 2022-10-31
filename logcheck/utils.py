from pathlib import Path

from tree_sitter import Language, Parser

supported_languages = ["python"]


def create_tree_sitter_language_object(language: str) -> Language:
    """
    Creates a tree-sitter language library in the 'build' directory
    A given language library only needs to be built once across many executions.
    :param language: string containing the programming language to be analyzed
    :return: tree-sitter language object
    """
    lib_path = str(Path(Path(__file__).parent / "build/my-languages.so").resolve())
    lang_paths = [str(Path(Path(__file__).parent / ("tree-sitter-" + lang)).resolve()) for lang in supported_languages]
    Language.build_library(lib_path, lang_paths)
    ts_lang = Language(lib_path, language)
    return ts_lang


def create_parser(language):
    tree_lang = create_tree_sitter_language_object(language)
    parser = Parser()
    parser.set_language(tree_lang)
    return parser, tree_lang
