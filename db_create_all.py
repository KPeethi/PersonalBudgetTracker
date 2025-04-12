"""
Script to recreate the database tables based on current models.
"""

import logging
from app import app, db
import models  # This imports all models so they're registered with SQLAlchemy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database():
    """
    Update database schema based on models.
    """
    try:
        with app.app_context():
            logger.info("Creating tables based on current models...")
            db.create_all()
            logger.info("Database tables updated successfully.")
            return True
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        return False

if __name__ == "__main__":
    if update_database():
        logger.info("Database update completed successfully.")
    else:
        logger.error("Database update failed.")