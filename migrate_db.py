"""
Database migration script to update the user table with new fields for admin monitoring.
"""
from app import app, db
from sqlalchemy import text
from models import User, Expense

def run_migration():
    """Run the database migration"""
    with app.app_context():
        try:
            print("Starting database migration...")
            # Create new columns
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP'))
                conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE'))
                conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE'))
                conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS suspension_reason VARCHAR(255)'))
                conn.commit()
            
            print("Migration completed successfully!")
            print("New columns added to users table:")
            print("  - last_login: To track when users log in")
            print("  - is_active: To track if an account is active")
            print("  - is_suspended: To track if an account is suspended")
            print("  - suspension_reason: To store the reason for suspension")
            
            return True
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            return False

if __name__ == "__main__":
    run_migration()