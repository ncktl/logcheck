# Logcheck

Logcheck is a static analysis tool utilising [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) to check code for sufficient logging.

Using Tree-sitter allows us to analyse various programming languages in a relatively language-agnostic way.

## Setup

The Tree-sitter python bindings as well as pandas and scikit-learn are required:

```sh
python3 -m pip install tree_sitter pandas scikit-learn numpy tensorflow tensorflow-addons keras tqdm gensim imbalanced-learn
```

For the Jupyter notebooks, the following additional package is required (not listed in requirements.txt):

```sh
python3 -m pip install matplotlib 
```

To use the pre-trained random forest classifiers, they must be decompressed:
```sh
tar -jxvf python_logging_classifier.tbz2
tar -jxvf java_logging_classifier.tbz2
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
usage: logcheck.py [-h] [-e] [-t] [-m {rnd,lstm}] [-o OUTPUT] [-f] [-l {java,javascript,python}] [-d] [-a] [-x] [-c] path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -e, --extract         Enables feature extraction mode. Logcheck will output parameter vectors from its analysis instead of logging recommendations.
  -t, --train           Enables training mode.
  -m {rnd,lstm}, --model {rnd,lstm}
                        Specify the classifier model, either random forest (rnd) or LSTM (lstm).
  -o OUTPUT, --output OUTPUT
                        Specify the output path.
  -f, --force           Force overwrite of output file
  -l {java,javascript,python}, --language {java,javascript,python}
                        Specify the language.
  -d, --debug           Enable debug mode.
  -a, --alt             Also extract the context when in extraction mode.
  -x, --all             Extract features for all blocks instead of only those inside function definitions.Can't be used together with -a context extraction.
```

### Training
Logcheck can train and use either a random forest classifier from Scikit-learn or a neural network that includes an LSTM
layer from Tensorflow. It also comes with pre-trained classifiers, so **this is optional**. Training mode is enable with 
the -t argument. The language when training on more than one file is set with -l. The classifer type is 
specified with the -m argument

Example:

```sh
python3 logcheck.py -t -l python -m rnd <path to folder containg source code files, including those in further folders>
```

### Recommendation

By default, Logcheck will analyse the source code of the given file(s) and give recommendations for logging.

The classifer model must be specified with the -m argument.
Options are "rnd" for the random forest classifier and "lstm" for the neural network classifier. 

If a folder is given to analyze multiple files, the language must be specified.

Example:
```sh
python3 logcheck.py -m rnd <file to be analyzed>
```
or
```sh
python3 logcheck.py -l python -m rnd <path to repository folder>
```



### Manual feature extraction

To extract parameter vectors from files for learning a classifier, use the -e extract option like this:

```sh
python3 logcheck.py -e <path to file or directory to extract features from>
```

### Manual classification learning


The classifier can also be manually trained using a separate python script with an extract. 
It will use the extracted features in the given .csv file:

```sh
python3 classification_learner.py <path to extract .csv file>
```