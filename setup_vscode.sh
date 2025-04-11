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

echo "Creating .env file from example..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please update it with your database credentials."
else
    echo ".env file already exists. Skipping..."
fi

echo ""
echo "==============================================================="
echo "Setup complete! Next steps:"
echo "==============================================================="
echo "1. Update the .env file with your database credentials"
echo "2. Run the database initialization script: python init_database.py"
echo "3. Start the application: python main.py"
echo ""
echo "For more details, refer to INSTALLATION_VSCODE.md"
echo ""
echo "Press Enter to exit..."
read