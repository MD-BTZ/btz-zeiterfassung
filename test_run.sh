#!/bin/bash
# Script to test the application without activating the virtual environment

cd "$(dirname "$0")"
echo "Testing app.py directly..."

# Install required dependencies if needed
if [ ! -f ".deps_installed" ]; then
    echo "Installing dependencies..."
    pip install flask flask-bcrypt pytz
    touch .deps_installed
fi

# Run the application
python app.py
