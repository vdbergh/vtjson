#!/bin/sh

mypy bench.py test_vtjson.py vtjson.py --strict --explicit-package-bases
black *.py
isort --profile black *.py
flake8 --max-line-length 88 bench.py test_vtjson.py vtjson.py
mdl *.md docs/*.md
cat README.md | aspell -a --mode=markdown --personal=./ignore.txt |grep \&
