#!/bin/bash

echo "Setting up Expense Tracker for VS Code (macOS/Linux)..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found! Please install Python 3.8 or higher."
    echo "Visit https://www.python.org/downloads/"
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install flask flask-login flask-sqlalchemy flask-wtf email-validator gunicorn psycopg2-binary numpy pandas plotly werkzeug markupsafe antropic openai twilio sqlalchemy plaid-python requests trafilatura

echo "Setting up VS Code configuration..."
python setup_vscode_env.py

echo ""
echo "Setup complete!"
echo "Please refer to INSTALLATION_VSCODE.md for next steps."
echo ""
echo "Press Enter to exit..."
read