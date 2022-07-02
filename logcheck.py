from tree_sitter import Language, Parser
import sys
from pathlib import Path
import importlib
import argparse

supported_languages = ["java", "python"]
suf = {
    "java": ".java",
    "python": ".py"
}
rev_suf = dict(zip(suf.values(), suf.keys()))


def create_ts_lang_obj(language: str) -> Language:
    """
    Creates a tree-sitter language library in the 'build' directory
    A given language library only needs to be built once across many executions.
    :param language: string containing the programming language to be analyzed
    :return: tree-sitter language object
    """
    Language.build_library("build/my-languages.so", list("tree-sitter-" + lang for lang in supported_languages))
    ts_lang = Language("build/my-languages.so", language)
    return ts_lang


# Deprecated
def print_supported_languages():
    print(f"Supported languages: {supported_languages}", file=sys.stderr)


# Deprecated
def print_usage():
    print(f"Usage: python3 {__file__} [-[B|L] <language>] <filepath>", file=sys.stderr)
    print(f"Options: -B\t Batch mode", file=sys.stderr)
    print("If no language is specified, the analyzer will attempt to infer the language.", file=sys.stderr)
    print_supported_languages()


# Deprecated
def infer_language(file_path: Path):
    """
    Detects the programming language from the file extension
    :param file_path:
    :return: String containing programming language name
    """
    if file_path.suffix == ".py":
        return "python"
    elif file_path.suffix == ".java":
        return "java"
    # elif file_path.suffix == ".js":
    #    return "javascript"
    # elif file_path.suffix == ".hs":
    #    return "haskell"
    # Deprecated:
    else:
        print_supported_languages()
        sys.exit()


# Deprecated
def main(argv):
    """
    main program execution
    """
    arglen = len(argv)
    if arglen not in [2, 3, 4]:
        print_usage()
        sys.exit()
    file_path = Path(argv[-1])
    if not file_path.exists():
        print("File or path doesn't exist.", file=sys.stderr)
        print_usage()
        sys.exit()
    # python3 logcheck.py <file>
    if arglen == 2:
        prog_lang = infer_language(file_path)
    else:  # -> arglen == 4
        # python3 logcheck.py -L <language> <file>
        if argv[1].lower() in [(x + y) for x in ["", "-", "--"] for y in ["l", "lang", "language"]]:
            batch = False
        # python3 logcheck.py -B <language> <file>
        elif argv[1].lower() in [(x + y) for x in ["", "-", "--"] for y in ["b", "batch"]]:
            batch = True
        else:
            print_usage()
            sys.exit()
        prog_lang = argv[2].lower()
        if prog_lang not in supported_languages:
            print_supported_languages()
            sys.exit()
    with open(argv[-1]) as file:
        sourcecode = file.read()
        file.close()
    # Treesitter Language object
    tree_lang = create_ts_lang_obj(prog_lang)
    parser = Parser()
    parser.set_language(tree_lang)
    # Create abstract syntax tree
    tree = parser.parse(bytes(sourcecode, "utf8"))
    # Import the appropriate analyzer and instantiate it
    analysis_class = getattr(importlib.import_module(prog_lang + "_analyzer"), prog_lang.capitalize() + "Analyzer")
    analyzer = analysis_class(sourcecode, tree_lang, tree, file_path)
    # Start the analysis
    analyzer.analyze()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("path", type=Path)
    arg_parser.add_argument("-b", "--batch", action="store_true",
                            help="Enable batch mode. Logcheck will be run on all source code files of"
                                 "the given programming language found in the specified directory and "
                                 "subdirectories. Requires the -l / --language argument.")
    arg_parser.add_argument("-f", "--feature", action="store_true",
                            help="Enables feature extraction mode. Logcheck will output parameter "
                                 "vectors from its analysis instead of logging recommendations.")
    arg_parser.add_argument("-o", "--output", help="Specify the output file. NYI")
    arg_parser.add_argument("-l", "--language", type=str, choices=supported_languages,
                            help="Specify the language. This is required in batch mode.")
    args = arg_parser.parse_args()
    # Check arguments
    if not args.path.exists():
        arg_parser.error("Path does not exist.")
    if not args.batch and args.path.is_dir():
        arg_parser.error("Use batch mode when specifying directories.")
    if args.batch:
        if args.language is None:
            arg_parser.error("Batch option requires specification of language.")
    # Determine language if not specified
    elif args.language is None:
        try:
            args.language = rev_suf[args.path.suffix]
        except KeyError:
            arg_parser.error(f"Supported languages: {supported_languages}")
    # Create tree-sitter parser
    tree_lang = create_ts_lang_obj(args.language)
    parser = Parser()
    parser.set_language(tree_lang)
    # Go through file(s)
    if args.batch:
        files = args.path.glob(f"**/*{suf[args.language]}")
    else:
        files = [args.path]
    param_vectors = []
    for file in files:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        # Check if logging is imported. Python specific placeholder!
        if "import logging" in sourcecode:
            print(f"File: {file}")
            # Create abstract syntax tree
            tree = parser.parse(bytes(sourcecode, "utf8"))
            # Import the appropriate analyzer and instantiate it
            analysis_class = getattr(importlib.import_module(args.language + "_analyzer"),
                                     args.language.capitalize() + "Analyzer")
            analyzer = analysis_class(sourcecode, tree_lang, tree, args.path)
            # Start the analysis
            # TODO: Check for feature extraction here instead
            if args.feature:
                file_param_vecs = analyzer.fill_param_vecs_sliding()
                # param_vectors.append(file_param_vecs)
                param_vectors += file_param_vecs
                # for i in file_param_vecs:
                #     print(i)
    # print(param_vectors)
    with open("./features/demofile.txt", "w") as out:
        out.write("\n".join([str(x) for x in param_vectors]))
        out.write("\n")
        out.close()