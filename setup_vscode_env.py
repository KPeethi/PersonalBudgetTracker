"""
Expense Tracker VS Code Setup Script
------------------------------------
This script creates necessary configuration files for VS Code development.
"""
import os
import json

def create_vscode_config():
    """Create VS Code configuration files."""
    # Create .vscode directory if it doesn't exist
    os.makedirs(".vscode", exist_ok=True)
    
    # Create launch.json
    launch_config = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Python: Flask",
                "type": "python",
                "request": "launch",
                "module": "flask",
                "env": {
                    "FLASK_APP": "main.py",
                    "FLASK_DEBUG": "1"
                },
                "args": [
                    "run",
                    "--host=0.0.0.0",
                    "--port=5000",
                    "--no-debugger"
                ],
                "jinja": True,
                "justMyCode": True
            },
            {
                "name": "Python: Current File",
                "type": "python",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal",
                "justMyCode": True
            },
            {
                "name": "Python: Main Application",
                "type": "python",
                "request": "launch",
                "program": "main.py",
                "console": "integratedTerminal",
                "justMyCode": True
            }
        ]
    }
    
    with open(".vscode/launch.json", "w") as f:
        json.dump(launch_config, f, indent=4)
    
    # Create settings.json
    settings_config = {
        "python.linting.enabled": True,
        "python.linting.pylintEnabled": True,
        "python.formatting.provider": "black",
        "python.terminal.activateEnvironment": True,
        "terminal.integrated.profiles.windows": {
            "PowerShell": {
                "source": "PowerShell",
                "icon": "terminal-powershell"
            },
            "Command Prompt": {
                "path": "${env:windir}\\System32\\cmd.exe",
                "args": [],
                "icon": "terminal-cmd"
            }
        },
        "terminal.integrated.defaultProfile.windows": "Command Prompt",
        "python.defaultInterpreterPath": "${workspaceFolder}\\venv\\Scripts\\python.exe",
        "sqltools.connections": [
            {
                "name": "SQL Server - ExpenseDB",
                "server": "NAME\\SQLEXPRESS",
                "driver": "MSSQL",
                "database": "ExpenseDB",
                "authenticationType": "Integrated",
                "username": "",
                "password": ""
            }
        ],
        "files.exclude": {
            "**/__pycache__": True,
            "**/.pytest_cache": True,
            "**/.vscode": False,
            "**/venv": False
        },
        "editor.formatOnSave": True,
        "python.analysis.extraPaths": ["."],
        "[python]": {
            "editor.formatOnSave": True,
            "editor.defaultFormatter": "ms-python.python"
        },
        "[html]": {
            "editor.defaultFormatter": "vscode.html-language-features"
        }
    }
    
    with open(".vscode/settings.json", "w") as f:
        json.dump(settings_config, f, indent=4)
    
    print("VS Code configuration files created successfully in the .vscode directory.")

def create_env_example():
    """Create a .env.example file with required environment variables."""
    env_content = """# Expense Tracker Environment Variables
# Copy this file to .env and update with your values

# Database Configuration
# PostgreSQL (default for Replit)
# DATABASE_URL=postgresql://username:password@localhost/expense_tracker

# MySQL
# DATABASE_URL=mysql+pymysql://username:password@localhost/expense_tracker

# SQL Server with Windows Authentication
DATABASE_URL=mssql+pyodbc:///?odbc_connect=DRIVER={ODBC Driver 17 for SQL Server};SERVER=NAME\\SQLEXPRESS;DATABASE=ExpenseDB;Trusted_Connection=yes

# Plaid configuration
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=sandbox
PLAID_REDIRECT_URI=http://localhost:5000/plaid/oauth-callback

# OpenAI configuration
OPENAI_API_KEY=your-openai-api-key

# Session Secret
SESSION_SECRET=your-secret-key

# Python path configuration (for VSCode)
PYTHONPATH=${workspaceFolder}
"""

    with open(".env.example", "w") as f:
        f.write(env_content)
    
    print(".env.example file created. Copy to .env and update with your values.")

def create_python_path_file():
    """Create a .env file for Python path configuration if it doesn't exist."""
    # Check if .env file exists
    if os.path.exists(".env"):
        # Append Python path configuration if file exists
        with open(".env", "a") as f:
            f.write("\n# Python path configuration (for VSCode)\n")
            f.write("PYTHONPATH=${workspaceFolder}\n")
        print("Python path configuration appended to existing .env file.")
    else:
        # Create minimal .env file if it doesn't exist
        with open(".env", "w") as f:
            f.write("""# Database URL for SQL Server with Windows Authentication
DATABASE_URL=mssql+pyodbc:///?odbc_connect=DRIVER={ODBC Driver 17 for SQL Server};SERVER=NAME\\SQLEXPRESS;DATABASE=ExpenseDB;Trusted_Connection=yes

# Plaid configuration - replace with your actual values
PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox
PLAID_REDIRECT_URI=http://localhost:5000/plaid/oauth-callback

# OpenAI configuration - replace with your actual key
OPENAI_API_KEY=

# Session Secret
SESSION_SECRET=your-secret-key-change-in-production

# Python path configuration (for VSCode)
PYTHONPATH=${workspaceFolder}
""")
        print("Created new .env file with Python path configuration.")
    
    print("Note: Remember to update .env with your actual credentials and API keys.")

def main():
    """Main function to set up VS Code environment."""
    print("Setting up VS Code environment for Expense Tracker...")
    create_vscode_config()
    create_env_example()
    create_python_path_file()
    
    print("\nSetup complete! Next steps:")
    print("1. Install the recommended VS Code extensions")
    print("2. Copy .env.example to .env and update with your values")
    print("3. Set up a Python virtual environment")
    print("4. Install required packages")
    print("5. Initialize the database")
    print("\nSee INSTALLATION_VSCODE.md for detailed instructions.")

if __name__ == "__main__":
    main()