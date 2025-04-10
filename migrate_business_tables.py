"""
Script to create business-related database tables safely.
"""

import time
import logging
import sys
from sqlalchemy import inspect, text
from app import app, db
from models import User, BusinessUpgradeRequest, ExcelImport

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_if_table_exists(table_name):
    """Check if a table exists in the database."""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()

def add_business_user_field():
    """Add is_business_user column to users table if it doesn't exist."""
    logger.info("Checking if is_business_user field exists in users table...")
    with db.engine.connect() as conn:
        # Check if column exists
        column_exists_query = text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_business_user'
        )
        """)
        
        column_exists = conn.execute(column_exists_query).scalar()
        
        if not column_exists:
            logger.info("Adding is_business_user column to users table...")
            try:
                add_column_query = text("""
                ALTER TABLE users 
                ADD COLUMN is_business_user BOOLEAN NOT NULL DEFAULT false
                """)
                
                conn.execute(add_column_query)
                conn.commit()
                logger.info("Successfully added is_business_user column to users table.")
            except Exception as e:
                logger.error(f"Error adding is_business_user column: {str(e)}")
                return False
        else:
            logger.info("is_business_user column already exists in users table.")
        
        return True

def create_business_upgrade_requests_table():
    """Create the business_upgrade_requests table if it doesn't exist."""
    if check_if_table_exists('business_upgrade_requests'):
        logger.info("business_upgrade_requests table already exists.")
        return True
    
    logger.info("Creating business_upgrade_requests table...")
    try:
        with db.engine.connect() as conn:
            # Create the table manually to avoid conflicts with existing sequences
            create_table_query = text("""
            CREATE TABLE business_upgrade_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                status VARCHAR(20) DEFAULT 'pending',
                company_name VARCHAR(100) NOT NULL,
                industry VARCHAR(100),
                business_email VARCHAR(120),
                phone_number VARCHAR(20),
                reason TEXT,
                admin_notes TEXT,
                handled_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            conn.execute(create_table_query)
            conn.commit()
            logger.info("Successfully created business_upgrade_requests table.")
            return True
    except Exception as e:
        logger.error(f"Error creating business_upgrade_requests table: {str(e)}")
        return False

def create_excel_imports_table():
    """Create the excel_imports table if it doesn't exist."""
    if check_if_table_exists('excel_imports'):
        logger.info("excel_imports table already exists.")
        return True
    
    logger.info("Creating excel_imports table...")
    try:
        with db.engine.connect() as conn:
            # Create the table manually to avoid conflicts with existing sequences
            create_table_query = text("""
            CREATE TABLE excel_imports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(512) NOT NULL,
                file_size INTEGER NOT NULL,
                num_rows INTEGER,
                status VARCHAR(20) DEFAULT 'pending',
                error_message TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_date TIMESTAMP
            )
            """)
            
            conn.execute(create_table_query)
            conn.commit()
            logger.info("Successfully created excel_imports table.")
            return True
    except Exception as e:
        logger.error(f"Error creating excel_imports table: {str(e)}")
        return False

def main():
    """Main migration function."""
    with app.app_context():
        logger.info("Starting business tables migration...")
        
        # Add is_business_user field to users table
        if not add_business_user_field():
            logger.error("Failed to add is_business_user field. Aborting.")
            return False
        
        # Create business_upgrade_requests table
        if not create_business_upgrade_requests_table():
            logger.error("Failed to create business_upgrade_requests table. Aborting.")
            return False
        
        # Create excel_imports table
        if not create_excel_imports_table():
            logger.error("Failed to create excel_imports table. Aborting.")
            return False
        
        logger.info("Business tables migration completed successfully.")
        return True

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)