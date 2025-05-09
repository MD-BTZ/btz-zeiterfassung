#!/bin/bash
# Script to run the Flask application
cd "$(dirname "$0")"
source venv_new/bin/activate
python app.py