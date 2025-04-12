"""
Script to migrate expenses with import_id to excel_import_id.
This script fixes existing expenses that were created with import_id instead of excel_import_id.
"""

import logging
import sys
from app import app, db
from sqlalchemy import text
from models import Expense, ExcelImport

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_import_ids():
    """
    Update expenses with import_id to use excel_import_id instead.
    """
    with app.app_context():
        try:
            # First check if the import_id column exists
            try:
                result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='expenses' AND column_name='import_id'"))
                column_exists = result.scalar() is not None
                
                if not column_exists:
                    logger.info("The import_id column doesn't exist, nothing to migrate.")
                    return True
                
            except Exception as e:
                logger.error(f"Error checking for import_id column: {str(e)}")
                return False
            
            # First, get all expenses with import_id set
            # We need to use raw SQL since the model doesn't have import_id field anymore
            result = db.session.execute(text("SELECT id, import_id FROM expenses WHERE import_id IS NOT NULL"))
            
            count = 0
            for row in result:
                expense_id = row[0]
                import_id = row[1]
                
                # Update each expense to use excel_import_id
                db.session.execute(
                    text("UPDATE expenses SET excel_import_id = :import_id WHERE id = :expense_id"),
                    {"import_id": import_id, "expense_id": expense_id}
                )
                count += 1
            
            # If we found expenses to update, commit the changes
            if count > 0:
                db.session.commit()
                logger.info(f"Updated {count} expenses from import_id to excel_import_id")
            else:
                logger.info("No expenses found with import_id set")
            
            # Finally, drop the import_id column if it exists
            db.session.execute(
                text("ALTER TABLE expenses DROP COLUMN IF EXISTS import_id")
            )
            db.session.commit()
            logger.info("Dropped import_id column")
            
            return True
            
        except Exception as e:
            logger.error(f"Error migrating import_id to excel_import_id: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    logger.info("Starting migration from import_id to excel_import_id...")
    
    if migrate_import_ids():
        logger.info("Migration completed successfully.")
    else:
        logger.error("Migration failed.")
        sys.exit(1)