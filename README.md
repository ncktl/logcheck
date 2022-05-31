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