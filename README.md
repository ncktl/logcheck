# Logcheck

Logcheck is a static analysis tool utilising [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) to check code for sufficient logging.

Using Tree-sitter allows us to analyse various programming languages in a relatively language-agnostic way.

## Setup

The Tree-sitter python bindings as well as pandas and scikit-learn are required:

```sh
python3 -m pip install tree_sitter pandas scikit-learn
```

Additionally, the tree-sitter repository has to be cloned into the Logcheck direcory and built:
```sh
git clone https://github.com/tree-sitter/tree-sitter.git
cd tree-sitter/
make
cd ..
```
Finally, the grammars of the currently supported languages need to be cloned into the main logcheck folder as well:
```sh
git clone https://github.com/tree-sitter/tree-sitter-python.git
git clone https://github.com/tree-sitter/tree-sitter-java.git
```

I.e. the folder "tree-sitter-python/" must be inside the folder "logcheck". 

## Usage

```sh
usage: logcheck.py [-h] [-b] [-e] [-o OUTPUT] [-f] [-l {java,python}] [-m {bool,onehot}] [-s] path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -b, --batch           Enable batch mode. Logcheck will be run on all source code files of the 
                        given programming language found in the specified directory and 
                        subdirectories. Requires the -l / --language argument.
  -e, --extract         Enables feature extraction mode. Logcheck will output parameter vectors 
                        from its analysis instead of logging recommendations.
  -o OUTPUT, --output OUTPUT
                        Specify the output file.
  -f, --force           Force overwrite of output file
  -l {java,python}, --language {java,python}
                        Specify the language. Default: python
  -m {bool,onehot}, --mode {bool,onehot}
                        Mode of encoding. Default: bool
  -s, --suffix          Add mode of encoding to file name
```

### Feature extraction

To extract parameter vectors from files for learning a classifier, use the -e extract option like this:

```sh
python3 logcheck.py -e <file to extract features from>
```

Or extract parameter vectors from all files in a directory, using the -b batch option like so (recommended):

```sh
python3 logcheck.py -e -b <path to directory>
```

E.g. with the provided code examples:

```sh
python3 logcheck.py -e -b code-examples/
```

### Classification learning

The classifier can be retrained using its own python script. This will use the extracted features in the features/combination.csv file:

```sh
python3 classification_learner.py
```


### Recommendation

By default, Logcheck will analyse the source code of the given file(s) and give recommendations for logging.

```sh
python3 logcheck.py <file to be analyzed>
```

Generate logging recommendations for all files in a directory, using the -b batch option like so (recommended):

```sh
python3 logcheck.py -b <path to directory>
```

E.g. with the provided code examples:

```sh
python3 logcheck.py -b code-examples/
```