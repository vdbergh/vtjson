#!/bin/sh

black *.py
isort --profile black *.py
flake8 --max-line-length 88 bench.py test_validate.py vtjson.py
mdl *.md
