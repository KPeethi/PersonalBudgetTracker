# Budget AI - VS Code Installation with SQL Server

## Prerequisites

1. Python 3.8+ installed
2. SQL Server Express installed
3. SQL Server ODBC Driver 17 installed
4. Git installed

## Setup Steps

### 1. Clone the repository (if needed)

```bash
git clone https://github.com/yourusername/budget-ai.git
cd budget-ai
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Set up the `.env` file

Create a `.env` file in the project root with the following content (already provided in the project):

```
DATABASE_URL=mssql+pyodbc:///?odbc_connect=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=budget_ai;Trusted_Connection=yes
FLASK_SECRET_KEY=myRandomSecretKey123!
SESSION_SECRET=myRandomSecretKey123!
```

This connection string uses Windows Authentication (Trusted Connection) to connect to your local SQL Server Express instance. You may need to adjust:
- The `SERVER` value if your SQL Server instance has a different name than SQLEXPRESS
- The `DATABASE` value if you want to use a different database name
```

### 6. Create the database

Run the `create_database.sql` script in SQL Server Management Studio to create the database.

### 7. Set up the tables

```bash
python setup_mssql.py
```

This script will create all necessary tables in your database.

### 8. Start the application

```bash
python main.py
```

The application will be available at http://localhost:5000

## Using VS Code Tasks

This project includes VS Code tasks to make common operations easier:

1. Press `Ctrl+Shift+P` to open the Command Palette
2. Type "Tasks: Run Task" and select it
3. Choose from the available tasks:
   - "Run Budget AI" - Starts the application normally (requires login)
   - "Run Budget AI - Test Mode" - Starts in test mode without login requirements
   - "Initialize Database" - Sets up the database tables
   - "Create Admin User" - Creates an admin user

## Test Mode for Developers and Testers

For testing purposes, you can run the application in test mode which bypasses all login requirements:

```bash
python test_app.py
```

This will:
1. Start the app on port 5001 (regular app uses port 5000)
2. Automatically create a test user with admin and business user privileges
3. Allow access to all parts of the application without login
4. Show a test mode indicator at the top of the page

**Warning**: Test mode should only be used during development and testing, not in production environments.

## Troubleshooting

### ODBC Driver Issues

If you get errors about the ODBC driver, make sure you have installed the SQL Server ODBC Driver 17. You can download it from Microsoft's website.

### Authentication Issues

If you're having issues with Windows Authentication, try modifying your connection string in the `.env` file to use Trusted Connection.

### Database Connection Issues

If you can't connect to the database, verify these things:
1. SQL Server Express is running
2. Windows Authentication is enabled
3. Your Windows user has permissions to access the database
4. The database name in your connection string matches the actual database name

### Importing from Existing Database

If you have an existing database with expense data, you can use the SQL import functionality:

```bash
python -c "from sql_import import import_expenses_from_sql_file; import_expenses_from_sql_file('path/to/your_data.sql', user_id=1)"
```