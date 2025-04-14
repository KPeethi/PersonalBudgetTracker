"""
SQL Server setup script for Budget AI application.
Creates all necessary tables and admin user.
"""
import logging
import sys
import os
from sqlalchemy import create_engine, text, inspect
from werkzeug.security import generate_password_hash

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.info("Python-dotenv not installed, using environment variables directly")

# Get database connection URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    sys.exit(1)

# Create database engine
engine = create_engine(DATABASE_URL)

def execute_sql(sql, params=None):
    """Execute SQL safely with proper error handling."""
    try:
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(sql), params)
            else:
                result = conn.execute(text(sql))
            conn.commit()
            return True, result
    except Exception as e:
        logger.error(f"SQL Error: {str(e)}")
        return False, None

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def create_tables():
    """Create all necessary tables for Budget AI application."""
    
    # Create users table
    if not check_table_exists('users'):
        logger.info("Creating users table...")
        users_sql = """
        CREATE TABLE users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(64) NOT NULL UNIQUE,
            email NVARCHAR(120) NOT NULL UNIQUE,
            password_hash NVARCHAR(256) NOT NULL,
            created_at DATETIME DEFAULT GETDATE(),
            is_admin BIT DEFAULT 0,
            is_business_user BIT DEFAULT 0,
            last_login DATETIME NULL,
            is_active BIT DEFAULT 1,
            is_suspended BIT DEFAULT 0,
            suspension_reason NVARCHAR(255) NULL
        )
        """
        success, _ = execute_sql(users_sql)
        if not success:
            return False
        logger.info("Users table created successfully")
    else:
        logger.info("Users table already exists")
    
    # Create expenses table
    if not check_table_exists('expenses'):
        logger.info("Creating expenses table...")
        expenses_sql = """
        CREATE TABLE expenses (
            id INT IDENTITY(1,1) PRIMARY KEY,
            date DATE NOT NULL DEFAULT GETDATE(),
            description NVARCHAR(255) NOT NULL,
            category NVARCHAR(100) NOT NULL,
            amount FLOAT NOT NULL,
            user_id INT NULL REFERENCES users(id),
            created_at DATETIME DEFAULT GETDATE(),
            payment_method NVARCHAR(50) NULL,
            merchant NVARCHAR(100) NULL,
            excel_import_id INT NULL
        )
        """
        success, _ = execute_sql(expenses_sql)
        if not success:
            return False
        logger.info("Expenses table created successfully")
    else:
        logger.info("Expenses table already exists")
    
    # Create budgets table
    if not check_table_exists('budgets'):
        logger.info("Creating budgets table...")
        budgets_sql = """
        CREATE TABLE budgets (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id),
            total_budget FLOAT DEFAULT 3000.0,
            food FLOAT DEFAULT 500.0,
            transportation FLOAT DEFAULT 300.0,
            entertainment FLOAT DEFAULT 200.0,
            bills FLOAT DEFAULT 800.0,
            shopping FLOAT DEFAULT 400.0,
            other FLOAT DEFAULT 800.0,
            month INT DEFAULT DATEPART(month, GETDATE()),
            year INT DEFAULT DATEPART(year, GETDATE()),
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE()
        )
        """
        success, _ = execute_sql(budgets_sql)
        if not success:
            return False
        logger.info("Budgets table created successfully")
    else:
        logger.info("Budgets table already exists")
    
    # Create business_upgrade_requests table
    if not check_table_exists('business_upgrade_requests'):
        logger.info("Creating business_upgrade_requests table...")
        business_requests_sql = """
        CREATE TABLE business_upgrade_requests (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id),
            status NVARCHAR(20) DEFAULT 'pending',
            company_name NVARCHAR(100) NOT NULL,
            industry NVARCHAR(100) NULL,
            business_email NVARCHAR(120) NULL,
            phone_number NVARCHAR(20) NULL,
            reason NVARCHAR(MAX) NULL,
            admin_notes NVARCHAR(MAX) NULL,
            handled_by INT NULL REFERENCES users(id),
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE()
        )
        """
        success, _ = execute_sql(business_requests_sql)
        if not success:
            return False
        logger.info("Business_upgrade_requests table created successfully")
    else:
        logger.info("Business_upgrade_requests table already exists")
    
    # Create excel_imports table
    if not check_table_exists('excel_imports'):
        logger.info("Creating excel_imports table...")
        excel_imports_sql = """
        CREATE TABLE excel_imports (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id),
            filename NVARCHAR(255) NOT NULL,
            file_path NVARCHAR(512) NOT NULL,
            file_size INT NOT NULL,
            num_rows INT NULL,
            records_imported INT NULL,
            status NVARCHAR(20) DEFAULT 'pending',
            error_message NVARCHAR(MAX) NULL,
            description NVARCHAR(MAX) NULL,
            upload_date DATETIME DEFAULT GETDATE(),
            completed_at DATETIME NULL,
            created_at DATETIME DEFAULT GETDATE()
        )
        """
        success, _ = execute_sql(excel_imports_sql)
        if not success:
            return False
        logger.info("Excel_imports table created successfully")
    else:
        logger.info("Excel_imports table already exists")
    
    # Add more tables as needed
    
    return True

def create_admin_user():
    """Create admin user if it doesn't exist."""
    # Check if admin exists
    check_sql = "SELECT COUNT(*) FROM users WHERE email = 'admin@example.com'"
    success, result = execute_sql(check_sql)
    
    if success:
        count = result.scalar()
        if count == 0:
            logger.info("Creating admin user...")
            # Hash the password
            password_hash = generate_password_hash("Password123!")
            
            # Insert admin user
            insert_sql = """
            INSERT INTO users (username, email, password_hash, is_admin, is_active)
            VALUES ('admin', 'admin@example.com', :password_hash, 1, 1)
            """
            success, _ = execute_sql(insert_sql, {"password_hash": password_hash})
            if success:
                logger.info("Admin user created successfully")
                return True
            else:
                logger.error("Failed to create admin user")
                return False
        else:
            logger.info("Admin user already exists")
            return True
    else:
        logger.error("Failed to check for existing admin user")
        return False

def main():
    """Main function to set up the database."""
    logger.info("Starting Budget AI SQL Server setup...")
    
    # Create tables
    if not create_tables():
        logger.error("Failed to create tables")
        return False
    
    # Create admin user
    if not create_admin_user():
        logger.error("Failed to create admin user")
        return False
    
    logger.info("Budget AI SQL Server setup completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
    sys.exit(0)