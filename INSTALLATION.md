# Expense Tracker Installation Guide

This guide will help you set up the Expense Tracker application on your own server with MySQL.

## Prerequisites

1. Python 3.9+ installed
2. MySQL Server installed and running
3. A web server (optional, for production deployment)

## Step 1: Database Setup

1. Create a new MySQL database named `ExpenseDB` (or any name you prefer):

```sql
CREATE DATABASE ExpenseDB;
```

2. Create a MySQL user with access to this database or use an existing user.

## Step 2: Application Setup

1. Download the expense tracker code from the provided source.

2. Open the `config.py` file and update the database connection settings:

```python
# Update with your MySQL credentials
DATABASE_URL = "mysql+pymysql://username:password@localhost/ExpenseDB"
```

Replace `username` and `password` with your MySQL credentials.

3. Install the required Python packages using the requirements included in the project.

## Step 3: Initialize the Database

Run the following command to create the necessary database tables:

```bash
python -c "from app import create_app; app = create_app(); from models import User, Expense"
```

## Step 4: Create an Admin User

Run the following command to create an admin user:

```bash
python create_admin.py
```

Follow the prompts to set up your admin username, email, and password.

## Step 5: Starting the Application

For development:

```bash
flask run --host=0.0.0.0 --port=5000
```

Or use Python directly:

```bash
python main.py
```

For production, we recommend using Gunicorn:

```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## Step 6: Access the Application

Open your web browser and navigate to:

```
http://localhost:5000
```

Or if you are accessing from another machine, use your server IP address:

```
http://your_server_ip:5000
```

## Using the CLI Version (Optional)

You can also use the command-line interface version:

```bash
python expense_tracker.py
```

## Troubleshooting

### Database Connection Issues

If you experience database connection issues:

1. Check that your MySQL server is running
2. Verify your database credentials in `config.py`
3. Ensure the database exists
4. Make sure the user has the necessary permissions

### Plaid API Connection

If you need to use the Plaid API, make sure you update the Plaid credentials in `config.py`.

## Security Notes

- For production, set a strong secret key in `config.py`
- Store sensitive credentials as environment variables rather than directly in the code
- Use HTTPS in production
- Regularly update dependencies to address security issues
