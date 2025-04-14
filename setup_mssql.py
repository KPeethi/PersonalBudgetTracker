"""
SQL Server setup script for the Budget AI application.
This script creates all necessary database tables for SQL Server.
"""

import os
import sys
import time
from sqlalchemy import text, inspect
import werkzeug.security

# Handle relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, using environment variables directly")

# Import Flask app and database
try:
    from app import app, db
    from models import User
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

def check_database_connection():
    """Verify database connection."""
    try:
        with app.app_context():
            # Test the connection by executing a simple query
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

def check_if_table_exists(table_name):
    """Check if a table exists in the database."""
    with app.app_context():
        inspector = inspect(db.engine)
        return table_name in inspector.get_table_names()

def create_tables():
    """Create all database tables."""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("All tables created successfully!")
            return True
        except Exception as e:
            print(f"Error creating tables: {e}")
            return False

def create_admin_user():
    """Create an admin user if no users exist."""
    with app.app_context():
        try:
            user_count = User.query.count()
            if user_count == 0:
                # Create admin user
                admin = User(
                    username="admin",
                    email="admin@example.com",
                    password_hash=werkzeug.security.generate_password_hash("Password123!"),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created: admin@example.com / Password123!")
                return True
            else:
                print(f"Users already exist in the database ({user_count} found). Skipping admin creation.")
                return True
        except Exception as e:
            print(f"Error creating admin user: {e}")
            return False

def add_business_user_field():
    """Add is_business_user column to users table if it doesn't exist."""
    with app.app_context():
        try:
            print("Checking if is_business_user field exists in users table.")
            with db.engine.connect() as conn:
                # Check if column exists - SQL Server syntax
                column_exists_query = text("""
                SELECT COUNT(*) AS column_exists
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='is_business_user'
                """)
                
                result = conn.execute(column_exists_query)
                column_exists = result.scalar() > 0
                
                if not column_exists:
                    print("Adding is_business_user column to users table...")
                    # SQL Server syntax for adding a column
                    add_column_query = text("""
                    ALTER TABLE users 
                    ADD is_business_user BIT NOT NULL DEFAULT 0
                    """)
                    
                    conn.execute(add_column_query)
                    print("Successfully added is_business_user column to users table.")
                else:
                    print("is_business_user column already exists in users table.")
            
            return True
        except Exception as e:
            print(f"Error adding is_business_user field: {e}")
            return False

def create_business_upgrade_requests_table():
    """Create the business_upgrade_requests table if it doesn't exist."""
    with app.app_context():
        if check_if_table_exists('business_upgrade_requests'):
            print("business_upgrade_requests table already exists.")
            return True
        
        try:
            print("Creating business_upgrade_requests table...")
            with db.engine.connect() as conn:
                # Create the table with SQL Server compatible syntax
                create_table_query = text("""
                CREATE TABLE business_upgrade_requests (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INTEGER NOT NULL FOREIGN KEY REFERENCES users(id),
                    status VARCHAR(20) DEFAULT 'pending',
                    company_name VARCHAR(100) NOT NULL,
                    industry VARCHAR(100),
                    business_email VARCHAR(120),
                    phone_number VARCHAR(20),
                    reason TEXT,
                    admin_notes TEXT,
                    handled_by INTEGER FOREIGN KEY REFERENCES users(id),
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                )
                """)
                
                conn.execute(create_table_query)
                print("Successfully created business_upgrade_requests table.")
                return True
        except Exception as e:
            print(f"Error creating business_upgrade_requests table: {e}")
            return False

def create_excel_imports_table():
    """Create the excel_imports table if it doesn't exist."""
    with app.app_context():
        if check_if_table_exists('excel_imports'):
            print("excel_imports table already exists.")
            return True
        
        try:
            print("Creating excel_imports table...")
            with db.engine.connect() as conn:
                # Create the table with SQL Server compatible syntax
                create_table_query = text("""
                CREATE TABLE excel_imports (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INTEGER NOT NULL FOREIGN KEY REFERENCES users(id),
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(512) NOT NULL,
                    file_size INTEGER NOT NULL,
                    num_rows INTEGER,
                    records_imported INTEGER,
                    status VARCHAR(20) DEFAULT 'pending',
                    error_message TEXT,
                    description TEXT,
                    upload_date DATETIME DEFAULT GETDATE(),
                    completed_at DATETIME,
                    created_at DATETIME DEFAULT GETDATE()
                )
                """)
                
                conn.execute(create_table_query)
                print("Successfully created excel_imports table.")
                return True
        except Exception as e:
            print(f"Error creating excel_imports table: {e}")
            return False

def main():
    """Main setup function."""
    print("-" * 50)
    print("Budget AI - SQL Server Setup")
    print("-" * 50)
    
    # Step 1: Check database connection
    print("\nStep 1: Checking database connection...")
    if not check_database_connection():
        print("Database connection failed. Please check your connection string.")
        return False
    
    # Step 2: Create all tables
    print("\nStep 2: Creating database tables...")
    if not create_tables():
        print("Failed to create tables. Aborting setup.")
        return False
    
    # Step 3: Create admin user
    print("\nStep 3: Creating admin user...")
    if not create_admin_user():
        print("Failed to create admin user. Aborting setup.")
        return False
    
    # Step 4: Add business user field
    print("\nStep 4: Adding business user field...")
    if not add_business_user_field():
        print("Failed to add business user field. Aborting setup.")
        return False
    
    # Step 5: Create business upgrade requests table
    print("\nStep 5: Creating business upgrade requests table...")
    if not create_business_upgrade_requests_table():
        print("Failed to create business upgrade requests table. Aborting setup.")
        return False
    
    # Step 6: Create excel imports table
    print("\nStep 6: Creating excel imports table...")
    if not create_excel_imports_table():
        print("Failed to create excel imports table. Aborting setup.")
        return False
    
    print("\nSetup completed successfully!")
    print("-" * 50)
    print("You can now start the application by running:")
    print("python main.py")
    print("-" * 50)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)