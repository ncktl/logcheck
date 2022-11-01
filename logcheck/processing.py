import importlib
import logging
import os
import pickle
import sys
import pandas as pd
import numpy as np

from transformers import AutoTokenizer, AutoModelWithLMHead, SummarizationPipeline
from sklearn.ensemble import RandomForestClassifier
from tqdm import tqdm
from tree_sitter import Parser
from .utils import create_tree_sitter_language_object, create_parser
from .extractors.python_extractor import PythonExtractor
from .config import par_vec_onehot, reindex, par_vec_onehot_expanded, par_vec_zhenhao


doc_pipeline = SummarizationPipeline(
    model=AutoModelWithLMHead.from_pretrained("SEBIS/code_trans_t5_base_code_documentation_generation_python"),
    tokenizer=AutoTokenizer.from_pretrained("SEBIS/code_trans_t5_base_code_documentation_generation_python",
                                            skip_special_tokens=True))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("LogCheck")


def extract(files, settings, train_mode: bool = True):
    """ Extracts parameter vectors from the file(s) """
    # Catch permission errors before program execution
    try:
        out = open(settings.output, "w") if settings.output else sys.stdout
    except PermissionError as e:
        logger.error(e)
    parser, tree_lang = create_parser(settings.language)
    param_vectors = []
    for file in tqdm(files):
        try:
            with open(file) as f:
                sourcecode = f.read()
                f.close()
        except UnicodeDecodeError as e:
            logger.error(f"Encountered UnicodeDecodeError in file {file}:\n{e}")
            continue

        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Import the appropriate extractor and instantiate it
        extractor_class = getattr(importlib.import_module(settings.language + "_extractor"),
                                  settings.language.capitalize() + "Extractor")
        extractor = extractor_class(sourcecode, tree_lang, tree, settings)
        # Start the extraction
        if settings.zhenhao:
            file_param_vectors = extractor.fill_param_vecs_zhenhao(training=train_mode)  # Zhenhao
        else:
            file_param_vectors = extractor.fill_param_vecs_ast_new(training=train_mode)  # Regular
        if settings.debug:
            param_vectors += ["/" + str(file) + "y"]
        param_vectors += file_param_vectors
    if settings.zhenhao:
        param_vec_used = par_vec_zhenhao
    elif settings.alt:
        param_vec_used = par_vec_onehot_expanded
    else:
        param_vec_used = par_vec_onehot
        # Write output
    return param_vec_used


def log_recommendation(sourcecode, settings):
    """ Recommend logging for a file"""
    tree_lang = create_tree_sitter_language_object(settings.language)
    parser = Parser()
    parser.set_language(tree_lang)
    output = []
    classifier: RandomForestClassifier = pickle.load(
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models/classifier'), 'rb'))
    # Create abstract syntax tree
    tree = parser.parse(bytes(sourcecode, "utf8"))
    # Import the appropriate extractor and instantiate it
    extractor_class = PythonExtractor
    extractor = extractor_class(sourcecode, tree_lang, tree, settings)
    # Build a list of parameter vectors for all interesting nodes in the current file
    file_param_vectors = extractor.fill_param_vecs_ast_new(training=False)
    # print(df.to_string())
    if file_param_vectors:
        # Build Pandas DataFrame from the list of parameter vectors
        df = pd.DataFrame.from_dict(file_param_vectors)
        x = df.drop(["contains_logging", "location"], axis=1)
        # X = df.drop(["contains_logging"], axis=1)
        # One-hot encode the parameters type and parent
        x = pd.get_dummies(x, columns=["type", "parent"])
        # Reindex the dataframe to ensure all possible type and parent values are present as columns
        x = x.reindex(reindex, fill_value=0, axis="columns")
        # print(classifier.predict(df))
        # Predict logging for the parameter vectors, creating a list of booleans for the parameter vectors
        predictions = classifier.predict_proba(x)
        recs = np.where(predictions[:, 0] > 0.99, 1, 0)
        df['predictions'] = recs
        # Write the yes-instances as recommendations to the output file
        if (1 in recs) or (2 in recs):
            for i, prediction in enumerate(recs):
                if prediction:
                    file_param_vectors[i]['location']['log_message'] = \
                        "# logging.debug(\"" + \
                        doc_pipeline([file_param_vectors[i]['location']['text']])[0]['summary_text'] + "\")"

                    output.append(file_param_vectors[i]['location'])
    return sorted(output, key=lambda d: d['start_line_number'])
