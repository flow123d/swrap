#!/bin/bash
echo "Creating python environment.."
python3 -m venv --system-site-packages venv

source venv/bin/activate
python3 --version
which python
which pip
pip install --upgrade pip
pip -V

# if not included in docker image
pip install mpi4py ruamel.py

deactivate
