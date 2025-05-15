#!/bin/bash
# Script to run the Flask application
cd "$(dirname "$0")"
source venv/bin/activate
python app.py