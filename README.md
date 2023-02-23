# Logcheck

Logcheck is a language-agnostic framework for recommending logging statements. 
It currently offers implementations for Python and Java.

## Setup

Install the dependencies:

```sh
pip install -r requirements.txt
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

As a result the folders "tree-sitter" and "tree-sitter-python" should be inside the folder "logcheck". 

## Usage

```
usage: logcheck.py [-t] [-m {rnd,lstm}] [-o OUTPUT] [-f] [-l {java,python}] [-a] [-x] path

Positional arguments:
  path                  The file or folder containing files to predict or train on.
                        Files in subdirectories are included.

Optional arguments:
  -h, --help            Show help 
  -m {rnd,lstm}, --model {rnd,lstm}
                        Specify classifier model, either random forest (rnd) or LSTM (lstm).
                        Required for both prediction and training.
  -o OUTPUT, --output OUTPUT
                        Specify the output path. By default logcheck will print to stdout.
  -f, --force           Force overwrite of output file
  -l {java,python}, --language {java,python}
                        Specify the language.
  -t, --train           Enables training mode.

Further options for advanced usage:
  -e, --extract         Enables feature extraction mode.
  -a, --alt             Also extract the context when in extraction mode.
  -x, --all             Extract all blocks instead of only those inside function definitions.
                        Can't be used together with -a context extraction.
```

### Recommendation

By default, Logcheck will analyse the source code of the given file(s) and give recommendations for logging.

The classifier model must be specified with the -m argument.
Options are "rnd" for the random forest classifier and "lstm" for the neural network classifier. 

If a folder is given to analyze multiple files, the language must be specified.

Example:
```sh
python3 logcheck.py -m lstm <file to be analyzed>
```
or
```sh
python3 logcheck.py -l python -m rnd <path to repository folder>
```

### Training
Logcheck can train and use either a random forest classifier from Scikit-learn or a neural network that includes an LSTM
layer from Tensorflow. It also comes with pre-trained classifiers and neural network weights, so **this is optional**. 

Training mode is enabled with the -t argument. The language when training on more than one file is set with -l. 

The classifer type must be specified with the -m argument

Example:

```sh
python3 logcheck.py -t -l python -m rnd <path to folder>
```


## Further usage options



### Manual feature extraction

To extract block features from files for learning a classifier, use the -e extract argument. 
The output will be a .csv file.

```sh
python3 logcheck.py -e <path to file / folder>
```

To also extract the context feature, use the -a argument:

```sh
python3 logcheck.py -e -a <path to file / folder>
```

By default, only blocks descended from function/method definitions are extracted.
Extract all blocks using the -x argument. This can not be combined with context extraction (-a)

```sh
python3 logcheck.py -e -x <path to file / folder>
```

### Manual classification learning


The classifier can also be manually trained using a separate python script with an extract. 
It will use the extracted features in the given .csv file:

```sh
python3 classification_learner.py <path to extract .csv file>
```