"""
Database Initialization Script for Expense Tracker
-------------------------------------------------
This script initializes the database and creates tables for the application.
It also creates a default admin user for testing purposes.
"""
import os
import sys
from datetime import datetime, timezone

try:
    from app import app, db
    from models import User, Category, ExpenseType, BusinessUpgradeRequest
    from werkzeug.security import generate_password_hash
except ImportError:
    print("Error: Unable to import required modules.")
    print("Make sure you've activated your virtual environment and installed all dependencies.")
    sys.exit(1)

def initialize_database():
    """Initialize the database and create tables."""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✓ Database tables created successfully.")
            
            # Add default categories if they don't exist
            create_default_categories()
            
            # Create admin user if it doesn't exist
            create_admin_user()
            
            print("\nDatabase initialization complete!")
            print("You can now run the application with 'python main.py'")
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("\nPossible solutions:")
        print("1. Check your DATABASE_URL in the .env file")
        print("2. Make sure PostgreSQL is running")
        print("3. Create the database if it doesn't exist")
        sys.exit(1)

def create_default_categories():
    """Create default expense categories if they don't exist."""
    default_categories = [
        "Housing", "Transportation", "Food", "Utilities", 
        "Healthcare", "Insurance", "Debt", "Entertainment", 
        "Clothing", "Education", "Savings", "Gifts/Donations",
        "Travel", "Personal Care", "Miscellaneous"
    ]
    
    with app.app_context():
        existing_categories = [c.name for c in Category.query.all()]
        categories_to_add = []
        
        for category_name in default_categories:
            if category_name not in existing_categories:
                categories_to_add.append(Category(name=category_name))
        
        if categories_to_add:
            db.session.add_all(categories_to_add)
            db.session.commit()
            print(f"✓ Added {len(categories_to_add)} default categories.")
        else:
            print("✓ Default categories already exist.")
        
        # Add default expense types if they don't exist
        default_types = ["Fixed", "Variable", "Discretionary"]
        existing_types = [t.name for t in ExpenseType.query.all()]
        types_to_add = []
        
        for type_name in default_types:
            if type_name not in existing_types:
                types_to_add.append(ExpenseType(name=type_name))
        
        if types_to_add:
            db.session.add_all(types_to_add)
            db.session.commit()
            print(f"✓ Added {len(types_to_add)} default expense types.")
        else:
            print("✓ Default expense types already exist.")

def create_admin_user():
    """Create a default admin user if it doesn't exist."""
    with app.app_context():
        admin_email = "admin@example.com"
        if not User.query.filter_by(email=admin_email).first():
            admin_user = User(
                username="admin",
                email=admin_email,
                password_hash=generate_password_hash("Password123!"),
                is_admin=True,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"✓ Created admin user (admin@example.com / Password123!)")
        else:
            print("✓ Admin user already exists.")

if __name__ == "__main__":
    print("Initializing Expense Tracker database...\n")
    initialize_database()