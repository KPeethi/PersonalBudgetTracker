# VS Code Installation Guide for Expense Tracker

This guide will help you set up the Expense Tracker application in Visual Studio Code. Follow these steps to resolve the common issues that may appear in the VS Code environment.

## 1. Create a Virtual Environment

First, create a Python virtual environment to isolate the project dependencies:

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

## 2. Install Required Packages

Install all the required packages:

```bash
pip install flask flask-login flask-sqlalchemy flask-wtf email-validator psycopg2-binary pymysql requests plaid-python pandas plotly numpy openai markupsafe werkzeug gunicorn
```

## 3. Set Up Environment Variables

Create a `.env` file in the root directory of your project with the following content:

```
# Database Configuration
DATABASE_URL=sqlite:///expense_tracker.db
# For PostgreSQL, use something like:
# DATABASE_URL=postgresql://username:password@localhost:5432/expense_tracker

# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=True

# Plaid API Configuration
PLAID_CLIENT_ID=67a4290da237bf001e5c7ac6
PLAID_SECRET=02e5286ff3222322801b1649e99ca5
PLAID_ENV=sandbox
PLAID_REDIRECT_URI=http://localhost:5000/plaid/oauth-callback

# OpenAI API Configuration (if using AI features)
OPENAI_API_KEY=your-openai-api-key
```

## 4. Configure VS Code for Python

Make sure VS Code is properly configured for Python:

1. Install the Python extension for VS Code
2. Select the correct Python interpreter (the one from your virtual environment)
3. Configure the Python path in VS Code:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
   - Type "Python: Select Interpreter" and select the Python from your virtual environment

## 5. Configure VS Code Workspace Settings

Create a `.vscode` folder in your project root if it doesn't exist, then create a `settings.json` file inside with the following content:

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": false,
    "python.linting.mypyEnabled": false,
    "python.analysis.extraPaths": [
        "${workspaceFolder}"
    ],
    "python.envFile": "${workspaceFolder}/.env",
    "python.terminal.activateEnvironment": true
}
```

## 6. Install PostgreSQL (if using PostgreSQL)

If you're using PostgreSQL as your database, make sure to install PostgreSQL on your system and ensure that the `pg_config` executable is in your PATH.

For Windows:
1. During PostgreSQL installation, make sure to select the option to add PostgreSQL bin directory to the PATH
2. After installation, you may need to restart VS Code or your computer

For macOS (using Homebrew):
```bash
brew install postgresql
```

For Ubuntu/Debian:
```bash
sudo apt-get install postgresql postgresql-contrib libpq-dev
```

## 7. Configure launch.json (Optional)

For better debugging, create a `launch.json` file in the `.vscode` folder:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "main.py",
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1",
                "DATABASE_URL": "sqlite:///expense_tracker.db",
                "SECRET_KEY": "development-key",
                "PLAID_CLIENT_ID": "67a4290da237bf001e5c7ac6",
                "PLAID_SECRET": "02e5286ff3222322801b1649e99ca5",
                "PLAID_ENV": "sandbox",
                "PLAID_REDIRECT_URI": "http://localhost:5000/plaid/oauth-callback"
            },
            "args": [
                "run",
                "--no-debugger",
                "--host=0.0.0.0",
                "--port=5000"
            ],
            "jinja": true
        }
    ]
}
```

## 8. Additional VS Code Troubleshooting

### Fixing Common VS Code Errors

If you're seeing errors like the ones below in your VS Code problems tab:

- "Import X could not be resolved"
- "`msodl` is not defined"
- "`pyodbc` is not defined"
- "`a4290da237bf001e5c7ac6` is not defined"
- "`02e5286ff3222322801b1649e99ca5` is not defined"
- "`sandbox` is not defined"
- "`http` is not defined"
- "`rLzA` is not defined"

These are primarily due to:
1. Missing Python packages
2. Environment variables not properly loaded
3. VS Code's language server not detecting imports

To fix these issues:

1. Make sure you've installed all required packages in your virtual environment:
   ```bash
   pip install flask flask-login flask-sqlalchemy flask-wtf email-validator psycopg2-binary pymysql requests plaid-python pandas plotly numpy openai markupsafe werkzeug gunicorn python-dotenv
   ```

2. Add the python-dotenv package and update your code to load environment variables:
   ```bash
   pip install python-dotenv
   ```

3. Make sure your .env file contains all the necessary variables (see section 3)

4. Add this code at the top of config.py to load environment variables:
   ```python
   import os
   from dotenv import load_dotenv
   
   # Load environment variables from .env file
   load_dotenv()
   ```

5. For VS Code Language Server issues:
   - Update your Python extension for VS Code
   - Restart VS Code
   - Reload VS Code window: Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS), type "Reload Window" and press Enter
   - Force re-scan of your workspace: Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS), type "Python: Clear Cache and Reload" and press Enter

### Database Connection Issues

If you encounter database connection issues:

1. Make sure your `DATABASE_URL` is correctly set in your `.env` file
2. For PostgreSQL, ensure the database server is running
3. Check if you have the correct database drivers installed (`psycopg2-binary` for PostgreSQL or `pymysql` for MySQL)

### Plaid API Configuration

For Plaid API to work properly:

1. Make sure your Plaid API credentials are correctly set in your `.env` file
2. For local development, use the Sandbox environment
3. Ensure your `PLAID_REDIRECT_URI` is set correctly for your local environment

## 9. Running the Application

With the proper configuration in place, you can run the application from VS Code using:

1. The Run button in VS Code with the configured Flask launch profile
2. Or from the terminal in your virtual environment:
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

## Need Help?

If you encounter any issues not covered in this guide, please check:
- The official Flask documentation: https://flask.palletsprojects.com/
- VS Code Python extension documentation: https://code.visualstudio.com/docs/python/python-tutorial
- Plaid API documentation: https://plaid.com/docs/