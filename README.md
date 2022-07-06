# Logcheck

Logcheck is a static analysis tool utilising [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) to check code for sufficient logging.

Using Tree-sitter allows us to analyse various programming languages in a relatively language-agnostic way.

## Setup

The Tree-sitter python bindings are required:

```sh
pip3 install tree_sitter
```

Additionally, the tree-sitter repository has to be cloned into the Logcheck direcory and built:
```sh
git clone https://github.com/tree-sitter/tree-sitter.git
cd tree-sitter/
make
cd ..
```
Finally, the grammars of the currently supported languages need to be cloned as well:
```sh
git clone https://github.com/tree-sitter/tree-sitter-python.git
git clone https://github.com/tree-sitter/tree-sitter-java.git
```

## Usage

```sh
usage: logcheck.py [-h] [-b] [-e] [-o OUTPUT] [-f] [-l {java,python}] [-m {ast,sliding}] [-d] [-a] path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -b, --batch           Enable batch mode. Logcheck will be run on all source code files of the given programming language found in the specified directory and subdirectories.
                        Requires the -l / --language argument.
  -e, --extract         Enables feature extraction mode. Logcheck will output parameter vectors from its analysis instead of logging recommendations.
  -o OUTPUT, --output OUTPUT
                        Specify the output file.
  -f, --force           Force overwrite of output file
  -l {java,python}, --language {java,python}
                        Specify the language. This is required in batch mode.
  -m {ast,sliding}, --mode {ast,sliding}
                        Mode of extraction. Default: sliding
  -d, --debug           Enable debug mode
  -a, --alt             Use alternative / old functions
```

### Feature extraction

To extract parameter vectors from files, use the -e option like this:

```sh
python3 logcheck.py -e <file to extract features from>
```

The parameters are saved in features/demofile.csv (for now).

### Analysis

```sh
python3 logcheck.py <file to be analyzed>
```

By default, Logcheck will analyze the file and create a log file in the location of the provided code file with the name "analysis-of-filename.log"

Example code files for the currently provided languages are provided in the code-examples folder. Run the Python example like this:

```sh
python3 logcheck.py code-examples/simple-logging-example.py
```

and the Java example like this:
```sh
python3 logcheck.py code-examples/SimpleLoggingExample.java
```

### Batch mode

To process multiple files, use the -b option. It requires the specification of the programming language via the -l (small L) parameter like this:

```sh
python3 logcheck.py -e -b -l python code-examples/
```