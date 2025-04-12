"""
Script to add the description column to the excel_imports table.
"""

import os
import logging
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, Text
from app import app, db
from models import ExcelImport

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_description_column():
    """
    Add description column to excel_imports table.
    """
    try:
        with app.app_context():
            engine = db.engine
            metadata = MetaData()
            metadata.reflect(bind=engine)
            
            # Check if table exists
            if 'excel_imports' not in metadata.tables:
                logger.error("excel_imports table does not exist, migration aborted.")
                return False
            
            # Check if column already exists
            excel_imports = metadata.tables['excel_imports']
            if 'description' in excel_imports.c:
                logger.info("description column already exists in excel_imports table.")
                return True
            
            # Add the column
            logger.info("Adding description column to excel_imports table...")
            with engine.begin() as conn:
                conn.execute(f'ALTER TABLE excel_imports ADD COLUMN description TEXT;')
            
            logger.info("Successfully added description column to excel_imports table.")
            return True
    
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    if add_description_column():
        logger.info("Migration completed successfully.")
    else:
        logger.error("Migration failed.")
        sys.exit(1)