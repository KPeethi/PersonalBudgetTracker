"""
Migration script to add the excel_import_id column to the expenses table.
"""

import sys
import logging
from app import app, db
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_expenses_table():
    """
    Add excel_import_id column to expenses table.
    """
    try:
        # Connect to the database using the app's context
        with app.app_context():
            # Execute the ALTER TABLE command to add the new column
            db.session.execute(
                text("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS excel_import_id INTEGER")
            )
            
            # Add the foreign key constraint (optional, may fail if already exists)
            try:
                db.session.execute(
                    text("ALTER TABLE expenses ADD CONSTRAINT fk_excel_import "
                    "FOREIGN KEY (excel_import_id) REFERENCES excel_imports(id)")
                )
            except Exception as constraint_error:
                logger.warning(f"Could not add foreign key constraint: {str(constraint_error)}")
                # Continue execution - column creation is more important than the constraint
            
            # Commit the changes
            db.session.commit()
            
            logger.info("Successfully added excel_import_id column to expenses table.")
            return True
            
    except Exception as e:
        logger.error(f"Error adding excel_import_id column to expenses table: {str(e)}")
        # Don't try to rollback here as the app context might be gone
        return False

if __name__ == "__main__":
    logger.info("Starting migration to add excel_import_id column to expenses table...")
    
    if migrate_expenses_table():
        logger.info("Migration completed successfully.")
    else:
        logger.error("Migration failed.")
        sys.exit(1)