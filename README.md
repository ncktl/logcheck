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
python3 logcheck.py <file to be analyzed>
```

Logcheck will analyze the file and create a log file in the location of the provided code file with the name "analysis-of-filename.log"

Example code files for the currently provided languages are provided in the code-examples folder. Run the Python example like this:

```sh
python3 logcheck.py code-examples/simple-logging-example.py
```

and the Java example like this:
```sh
python3 logcheck.py code-examples/SimpleLoggingExample.java
```