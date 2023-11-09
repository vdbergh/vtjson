#!/bin/sh

VERSION=`python -c "import vtjson; print(vtjson.__version__)"`

python -m build
pip install -I dist/vtjson-$VERSION*whl
