# Expense Tracker - VSCode Installation Guide

This guide will walk you through setting up the Expense Tracker application in Visual Studio Code.

## Prerequisites

1. **Visual Studio Code**: [Download and install VS Code](https://code.visualstudio.com/)
2. **Python**: Version 3.8 or higher
3. **Git**: For version control
4. **PostgreSQL**: Database for storing application data

## Quick Setup (Recommended)

We've provided scripts to automate the setup process:

### For Windows:
1. Right-click `setup_vscode.bat` and select "Run as administrator"
2. Follow the on-screen instructions

### For macOS/Linux:
1. Open Terminal in the project directory
2. Make the script executable: `chmod +x setup_vscode.sh`
3. Run the script: `./setup_vscode.sh`
4. Follow the on-screen instructions

The scripts will:
- Create a Python virtual environment
- Install all required dependencies
- Set up VS Code configuration files
- Create template environment files

After running the script, skip to Step 4 (Database Setup) below.

## Manual Setup (Alternative)

If the automatic setup doesn't work for you, follow these manual steps:

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd expense-tracker
```

### Step 2: Set Up Python Environment

1. Open the project in VS Code
2. Open a terminal in VS Code (Terminal > New Terminal)
3. Create a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate the virtual environment
# For Windows:
venv\Scripts\activate
# For macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

Install the necessary packages:

```bash
pip install flask flask-login flask-sqlalchemy flask-wtf email-validator gunicorn 
pip install psycopg2-binary numpy pandas plotly werkzeug markupsafe
pip install antropic openai twilio sqlalchemy plaid-python requests trafilatura
```

### Step 3.5: Set Up VS Code Configuration

Run the setup script to create VS Code configuration files:

```bash
python setup_vscode_env.py
```

## Step 4: Set Up Database

1. Create a PostgreSQL database for the application
2. Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://username:password@localhost/expense_tracker
FLASK_SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key  # Optional for AI features
PLAID_CLIENT_ID=your-plaid-client-id  # Optional for Plaid integration
PLAID_SECRET=your-plaid-secret  # Optional for Plaid integration
PLAID_ENV=sandbox  # Optional for Plaid integration
```

Replace `username`, `password`, and other values with your actual credentials.

## Step 5: Database Setup

Run the database initialization script to set up the database with tables and default data:

```bash
# Initialize the database (creates tables and default admin user)
python init_database.py
```

This script will:
- Create all required database tables
- Add default expense categories
- Create a default admin user (admin@example.com / Password123!)

If you encounter any issues, ensure your database connection details in the `.env` file are correct and that your PostgreSQL server is running.

## Step 6: Install VS Code Extensions

Install the following VS Code extensions for a better development experience:

1. **Python**: For Python language support
2. **SQLTools**: For database management
3. **Jinja**: For improved HTML/Jinja2 template syntax highlighting
4. **Git Graph**: For visualizing Git history
5. **Better TOML**: For TOML file support

## Step 7: Configure VS Code for Debugging

1. Create a `.vscode` folder in your project (if it doesn't exist)
2. Create a `launch.json` file inside the `.vscode` folder:

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
                "FLASK_DEBUG": "1"
            },
            "args": [
                "run",
                "--host=0.0.0.0",
                "--port=5000",
                "--no-debugger"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```

## Step 8: Run the Application

1. Use the VS Code debugger by pressing F5 or clicking the Run and Debug icon
2. Alternatively, run the application from the terminal:

```bash
python main.py
```

3. Open your browser and navigate to: `http://localhost:5000`

## Admin Credentials

Use these credentials to access admin features:

- Email: admin@example.com
- Password: Password123!

## Troubleshooting

### Database Connection Issues

If you have trouble connecting to the database, verify:
- PostgreSQL is running
- Your database credentials in the `.env` file are correct
- The database exists and is accessible

### Missing Dependencies

If you encounter errors about missing modules:

```bash
pip install <missing-module>
```

### Port Already in Use

If port 5000 is already in use, you can change it in the `main.py` file or run:

```bash
python main.py --port=5001
```

## Development Tips

- Use VS Code's integrated terminal for running commands
- Use the debugger to set breakpoints and inspect variables
- Use the Git integration for version control
- Use the SQLTools extension to query the database directly
- Make use of VS Code's IntelliSense for Python and HTML/Jinja templates