#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python backend/manage.py collectstatic --noinput --ignore='node_modules/*'
