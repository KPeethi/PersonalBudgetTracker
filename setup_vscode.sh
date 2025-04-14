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
# Note: We're removing email-validator since we now use our own implementation
pip install flask flask-login flask-sqlalchemy flask-wtf gunicorn pyodbc numpy pandas plotly werkzeug markupsafe antropic openai twilio sqlalchemy plaid-python requests trafilatura python-dotenv

echo "Setting up VS Code configuration..."
python setup_vscode_env.py

# Create directories for SQL sample files if they don't exist
echo "Creating directories for sample files..."
mkdir -p static/templates

# Generate sample SQL import files
echo "Generating sample SQL import files..."
python -c "
import os
import sys
sys.path.insert(0, os.getcwd())
try:
    import sql_import
    os.makedirs('static/templates', exist_ok=True)
    sql_import.generate_sample_sql_import_file('static/templates/sample_import_postgresql.sql', 'postgresql')
    sql_import.generate_sample_sql_import_file('static/templates/sample_import_mysql.sql', 'mysql')
    sql_import.generate_sample_sql_import_file('static/templates/sample_import_mssql.sql', 'mssql')
    print('Sample SQL import files generated successfully')
except Exception as e:
    print(f'Error generating sample SQL files: {str(e)}')
"

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