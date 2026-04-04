#!/bin/sh

mypy bench.py test_vtjson.py vtjson.py --strict --explicit-package-bases
rm -rf env
python -m venv env
env/bin/python -m pip install dnspython email_validator idna python-magic typing_extensions
ty check --python env/bin/python --python-version 3.14 vtjson.py
black *.py
isort --profile black *.py
flake8 --max-line-length 88 bench.py test_vtjson.py vtjson.py
mdl *.md docs/*.md
cat README.md | aspell -a --mode=markdown --personal=./ignore.txt |grep \&
