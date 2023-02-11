import argparse
import importlib
import logging
import multiprocessing as mp
import pickle
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from tqdm import tqdm
from tree_sitter import Language, Parser

from config import supported_languages, suf, rev_suf
from config import parameter_vectors, rev_node_dicts, reindex


def create_ts_lang_obj(language: str) -> Language:
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


def extract_file(file, settings, LangExtractor, train_mode):
    """ Extracts features from a source code file and returns them as a list of parameter vectors (also lists) """

    # Read the source code
    try:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
    except UnicodeDecodeError as e:
        logger.error(f"Encountered UnicodeDecodeError in file {file}:\n{e}")
        return []
    except IsADirectoryError as e:
        logger.error(f"Encountered directory with a name ending like the language extension {file}:\n{e}")
        return []
    # Create Tree-Sitter language object and parser.
    # These could be reused for another source code file, but this is nontrivial due to parallelization.
    tree_lang = create_ts_lang_obj(settings.language)
    parser = Parser()
    parser.set_language(tree_lang)
    # Create abstract syntax tree
    tree = parser.parse(bytes(sourcecode, "utf8"))
    # Instantiate the language's extractor
    extractor = LangExtractor(sourcecode, tree_lang, tree, file, settings)
    # Start the extraction
    file_param_vecs = extractor.fill_param_vectors(training=train_mode)
    if settings.debug:
        file_param_vecs = ["/" + str(file) + "y"] + file_param_vecs
    return file_param_vecs


def extract(files, settings, LangExtractor, output, train_mode: bool = True):
    """ Starts parallelized feature extraction and writes the result to output """

    # Extract features from each file by calling extract_file() in parallel
    pool = mp.Pool(mp.cpu_count())
    # Async variant:
    # param_vectors = pool.starmap_async(extract_file, [(file, settings, train_mode) for file in files]).get()
    # Ordered parallelization:
    param_vectors = pool.starmap(extract_file, [(file, settings, LangExtractor, train_mode) for file in files])
    param_vectors = [par_vec for par_vec_list in param_vectors for par_vec in par_vec_list]
    pool.close()
    # Write output
    header = list(parameter_vectors[settings.language].keys())
    output.write(",".join(header) + "\n")
    output.write("\n".join(
        [str(x).replace(" ", "").replace("'", "")[1:-1] for x in param_vectors]))
    output.write("\n")


def recommend(files, settings, LangExtractor, output):
    """ Recommend logging """
    recommendations = []
    rev_node_dict = rev_node_dicts[settings.language]
    classifier: RandomForestClassifier = pickle.load(open('classifier', 'rb'))
    for file in tqdm(files):
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        # print(f"File: {file}")
        # Create tree-sitter parser
        tree_lang = create_ts_lang_obj(settings.language)
        parser = Parser()
        parser.set_language(tree_lang)
        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Instantiate the language's extractor
        extractor = LangExtractor(sourcecode, tree_lang, tree, file, settings)
        # Build a list of parameter vectors for all interesting nodes in the current file
        file_param_vecs = extractor.fill_param_vectors(training=False)
        # print(df.to_string())
        if file_param_vecs:
            # Build Pandas DataFrame from the list of parameter vectors
            df = pd.DataFrame.from_dict(file_param_vecs)
            # logger.debug(df); exit()
            X = df.drop(["contains_logging", "location", "context", "sibling_index"], axis=1)
            # X = df.drop(["contains_logging"], axis=1)
            # One-hot encode the parameters type and parent
            X = pd.get_dummies(X, columns=["type", "parent"])
            # Reindex the dataframe to ensure all possible type and parent values are present as columns
            X = X.reindex(reindex[settings.language], fill_value=0, axis="columns")
            # print(classifier.predict(df))
            # Predict logging for the parameter vectors, creating a list of booleans for the parameter vectors
            file_recommendations = classifier.predict(X)
            df['predictions'] = file_recommendations
            # Write the yes-instances as recommendations to the output file
            if 1 in file_recommendations:
                recommendations.append(f"File: {file}")
                for i, prediction in enumerate(file_recommendations):
                    if prediction:
                        line = file_param_vecs[i]['location'].split("-")[0].split(";")[0]
                        recommendations.append(f"We recommend logging in the "
                                               f"{rev_node_dict[file_param_vecs[i]['type']]} starting in line {line}")
    if recommendations:
        output.write("\n".join(recommendations))
    else:
        output.write("No recommendations")
    output.write("\n")
    output.close()


# DEPRECATED
def analyze():
    """ Calls analysis functions for development and debugging """
    # print("analyze")
    # print(settings.language)
    output = []
    for file in files:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        print(f"File: {file}")
        # Create tree-sitter parser
        tree_lang = create_ts_lang_obj(settings.language)
        parser = Parser()
        parser.set_language(tree_lang)
        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Import the appropriate analyzer and instantiate it
        analysis_class = getattr(importlib.import_module(settings.language + "_analyzer"),
                                 settings.language.capitalize() + "Analyzer")
        analyzer = analysis_class(sourcecode, tree_lang, tree, settings.path, settings)
        # Start the analysis
        file_analysis = analyzer.analyze()
        # output.append(f"{file}")
        # print(output)
        if file_analysis:
            output.append(f"File: {file}")
            output.extend(file_analysis)
    print("\n".join(output))


if __name__ == "__main__":
    # Handle arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("path", type=Path)
    arg_parser.add_argument("-e", "--extract", action="store_true",
                            help="Enables feature extraction mode. Logcheck will output parameter "
                                 "vectors from its analysis instead of logging recommendations.")
    arg_parser.add_argument("-o", "--output", type=Path,
                            help="Specify the output file.")
    arg_parser.add_argument("-f", "--force", action="store_true",
                            help="Force overwrite of output file")
    arg_parser.add_argument("-l", "--language", type=str, choices=supported_languages,
                            help="Specify the language.")
    arg_parser.add_argument("-d", "--debug", action="store_true",
                            help="Enable debug mode.")
    arg_parser.add_argument("-a", "--alt", action="store_true",
                            help="Also extract the context when in extraction mode.")
    arg_parser.add_argument("-x", "--all", action="store_true",
                            help="Extract features for all blocks instead of only those inside function definitions."
                                 "Can't be used together with -a context extraction.")
    arg_parser.add_argument("-c", "--encode", action="store_true",
                            help="ASCII encode type names to save space.")
    settings = arg_parser.parse_args()

    # Check arguments
    if not settings.path.exists():
        arg_parser.error("Path does not exist.")
    if settings.alt and settings.all:
        arg_parser.error("Can't build context while also extracting features for all blocks.")
    # Detect batch mode
    if settings.path.is_dir():
        batch = True
    elif settings.path.is_file():
        batch = False
    else:
        arg_parser.error("Path is neither file nor directory.")

    # Default output handling disabled in favor of printing to stdout
    # # Handle output
    # if not settings.output:
    #     # Feature extraction
    #     if settings.extract:
    #         if batch:
    #             settings.output = Path("features/demofile.csv")
    #             print(f"No output file specified. Using default: {settings.output}")
    #         else:
    #             settings.output = Path("features/" + settings.path.name + ".csv")
    #             print(f"No output file specified. Using: {settings.output}")
    #     # Analysis
    #     else:
    #         if batch:
    #             settings.output = Path("analysis/demofile.txt")
    #             print(f"No output file specified. Using default: {settings.output}")
    #         else:
    #             settings.output = Path("analysis/" + settings.path.name + ".txt")
    #             print(f"No output file specified. Using: {settings.output}")

    # File overwrite dialog
    if settings.output and settings.output.is_file() and not settings.force:
        def overwrite():
            force = input("Output file exists. Overwrite? [y/n]: ")
            if force.lower() in ["y", "yes"]:
                pass
            elif force.lower() in ["n", "no"]:
                print("Exiting")
                sys.exit()
            else:
                overwrite()
        overwrite()
    # Catch permission errors before program execution
    try:
        out = open(settings.output, "w") if settings.output else sys.stdout
    except PermissionError as e:
        arg_parser.error(e)
    # Ensure language is known
    if batch:
        if settings.language is None:
            arg_parser.error("Batch option requires specification of language.")
    # Without batch mode, determine language if not specified
    elif settings.language is None:
        try:
            settings.language = rev_suf[settings.path.suffix]
        except KeyError:
            arg_parser.error(f"Supported languages: {supported_languages}")
    # Determine files to work on
    if batch:
        files = list(settings.path.glob(f"**/*{suf[settings.language]}"))
    else:
        files = [settings.path]
    # Initialize logger
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("Logcheck")
    # Import the language's config and extractor
    # The extractor class has to be passed on as an argument due to parallelization
    if settings.language == "python":
        from python_extractor import PythonExtractor as LangExtractor
    elif settings.language == "java":
        from java_extractor import JavaExtractor as LangExtractor
    else:
        raise RuntimeError(f"{settings.language} is not actually supported yet.")
    # Branch into extraction or recommendation
    if settings.extract:
        extract(files, settings, LangExtractor, out)
    else:
        if settings.alt:
            analyze()
        else:
            recommend(files, settings, LangExtractor, out)
