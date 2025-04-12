"""
Migration script to add payment_method and merchant columns to the expenses table.
"""

import sys
import logging
from app import app, db
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_expenses_table():
    """
    Add payment_method and merchant columns to expenses table.
    """
    try:
        # Connect to the database using the app's context
        with app.app_context():
            # Execute the ALTER TABLE commands to add the new columns
            db.session.execute(
                text("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50)")
            )
            
            db.session.execute(
                text("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS merchant VARCHAR(100)")
            )
            
            # Commit the changes
            db.session.commit()
            
            logger.info("Successfully added payment_method and merchant columns to expenses table.")
            return True
            
    except Exception as e:
        logger.error(f"Error adding columns to expenses table: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting migration to add payment_method and merchant columns to expenses table...")
    
    if migrate_expenses_table():
        logger.info("Migration completed successfully.")
    else:
        logger.error("Migration failed.")
        sys.exit(1)