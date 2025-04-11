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
DATABASE_URL=postgresql://username:password@localhost/expense_tracker

# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key

# OpenAI API Configuration (Optional - for AI assistant features)
OPENAI_API_KEY=your-openai-api-key

# Plaid API Configuration (Optional - for bank integration)
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=sandbox
"""

    with open(".env.example", "w") as f:
        f.write(env_content)
    
    print(".env.example file created. Copy to .env and update with your values.")

def create_python_path_file():
    """Create a .env file for Python path configuration."""
    pythonpath_content = """PYTHONPATH=${workspaceFolder}
"""
    
    with open(".env", "w") as f:
        f.write(pythonpath_content)
    
    print("Python path configuration added to .env file.")

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