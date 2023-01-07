# Logcheck

Logcheck is a static analysis tool utilising [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) to check code for sufficient logging.

Using Tree-sitter allows us to analyse various programming languages in a relatively language-agnostic way.

## Setup

The Tree-sitter python bindings as well as pandas and scikit-learn are required:

```sh
python3 -m pip install tree_sitter pandas scikit-learn
```

For the Jupyter notebooks, the following additional packages are required (not listed in requirements.txt):

```sh
python3 -m pip install numpy matplotlib imblearn tensorflow keras gensim
```

Additionally, the tree-sitter repository has to be cloned into the Logcheck directory and built:
```sh
cd logcheck/
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

I.e. the folders "tree-sitter" and "tree-sitter-python" must be inside the folder "logcheck". 

## Usage

```
usage: logcheck.py [-h] [-e] [-o OUTPUT] [-f] [-l {java,javascript,python}] [-d] [-a] [-z] path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -e, --extract         Enables feature extraction mode. Logcheck will output parameter vectors
                        from its analysis instead of logging recommendations.
  -o OUTPUT, --output OUTPUT
                        Specify the output file.
  -f, --force           Force overwrite of output file
  -l {java,javascript,python}, --language {java,javascript,python}
                        Specify the language. Default: python
  -d, --debug           Enable debug mode.
  -a, --alt             Also extract the context when in extraction mode
```

### Feature extraction

To extract parameter vectors from files for learning a classifier, use the -e extract option like this:

```sh
python3 logcheck.py -e <path to file or directory to extract features from>
```

### Classification learning


The classifier can be retrained using its own python script. It will use the extracted features in the given .csv file:

```sh
python3 classification_learner.py <path to extract .csv file>
```


### Recommendation

By default, Logcheck will analyse the source code of the given file(s) and give recommendations for logging.

```sh
python3 logcheck.py <file to be analyzed>
```
