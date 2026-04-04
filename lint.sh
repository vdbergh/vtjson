#!/bin/sh

PYTHON=env/bin/python

python -m venv env
$PYTHON -m pip -q install black isort flake8 ty mypy pymongo dnspython email_validator idna python-magic typing_extensions  --upgrade
$PYTHON -m mypy bench.py test_vtjson.py vtjson.py --strict --explicit-package-bases
$PYTHON -m ty check --python env/bin/python --python-version 3.12 vtjson.py test_vtjson.py
$PYTHON -m black --target-version py312 *.py
$PYTHON -m isort --profile black *.py
$PYTHON -m flake8 --max-line-length 88 bench.py test_vtjson.py vtjson.py
mdl *.md docs/*.md
cat README.md | aspell -a --mode=markdown --personal=./ignore.txt |grep \&
