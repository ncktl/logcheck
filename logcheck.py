from tree_sitter import Language, Parser
import sys
from pathlib import Path
import importlib
import argparse
from extractor import par_vec, par_vec_extended

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


def extract():
    """ Extracts parameter vectors from the file(s) """
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
            # Import the appropriate extractor and instantiate it
            extractor_class = getattr(importlib.import_module(args.language + "_extractor"),
                                     args.language.capitalize() + "Extractor")
            extractor = extractor_class(sourcecode, tree_lang, tree, args.path, args)
            # Start the extraction
            if args.mode == "sliding":
                file_param_vecs = extractor.fill_param_vecs_sliding()
            else:
                if args.alt:
                    file_param_vecs = extractor.fill_param_vecs_ast()
                else:
                    file_param_vecs = extractor.fill_param_vecs_ast_new()
            if args.debug:
                param_vectors += [f" {file} "]
            param_vectors += file_param_vecs
    with open(args.output, "w") as out:
        if args.mode == "sliding":
            out.write(str(list(par_vec.keys()))[1:-1])
        else:
            if args.debug:
                out.write("Line," + ",".join(key for key in par_vec_extended.keys()))
            else:
                out.write(",".join(key for key in par_vec_extended.keys()))
        out.write("\n")
        out.write("\n".join([str(x)[1:-1] for x in param_vectors]))
        out.write("\n")
        out.close()


def analyze():
    """ Analyses the code in the file(s) """
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
            analyzer.analyze()
            # Todo: Output handling?


if __name__ == "__main__":
    # Handle arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("path", type=Path)
    arg_parser.add_argument("-b", "--batch", action="store_true",
                            help="Enable batch mode. Logcheck will be run on all source code files of"
                                 " the given programming language found in the specified directory and "
                                 "subdirectories. Requires the -l / --language argument.")
    arg_parser.add_argument("-e", "--extract", action="store_true",
                            help="Enables feature extraction mode. Logcheck will output parameter "
                                 "vectors from its analysis instead of logging recommendations.")
    arg_parser.add_argument("-o", "--output", type=Path,
                            help="Specify the output file.")
    arg_parser.add_argument("-f", "--force", action="store_true",
                            help="Force overwrite of output file")
    arg_parser.add_argument("-l", "--language", type=str, choices=supported_languages,
                            help="Specify the language. This is required in batch mode.")
    arg_parser.add_argument("-m", "--mode", type=str, choices=["ast", "sliding"], default="ast",
                            help="Mode of extraction. Default: ast")
    arg_parser.add_argument("-d", "--debug", action="store_true",
                            help="Enable debug mode")
    arg_parser.add_argument("-a", "--alt", action="store_true",
                            help="Use alternative / old functions")
    args = arg_parser.parse_args()
    # Check arguments
    if not args.path.exists():
        arg_parser.error("Path does not exist.")
    if not args.batch and args.path.is_dir():
        arg_parser.error("Use batch mode when specifying directories.")
    if args.output:
        if args.output.is_file() and not args.force:
            arg_parser.error("Output file exists. Use the -f argument to overwrite.")
    else:
        # Default output
        if args.batch:
            args.output = Path("features/demofile.csv")
        else:
            args.output = Path("features/" + args.path.name + ".csv")
    # Catch permission errors before program execution
    if args.extract:
        try:
            args.output.touch()
        except PermissionError as e:
            arg_parser.error(e)
    if args.batch:
        if args.language is None:
            arg_parser.error("Batch option requires specification of language.")
    # Without batch mode, determine language if not specified
    elif args.language is None:
        try:
            args.language = rev_suf[args.path.suffix]
        except KeyError:
            arg_parser.error(f"Supported languages: {supported_languages}")
    # Create tree-sitter parser
    tree_lang = create_ts_lang_obj(args.language)
    parser = Parser()
    parser.set_language(tree_lang)
    # Determine files to work on
    if args.batch:
        files = args.path.glob(f"**/*{suf[args.language]}")
    else:
        files = [args.path]
    # Branch into extraction or analysis
    if args.extract:
        extract()
    else:
        analyze()
