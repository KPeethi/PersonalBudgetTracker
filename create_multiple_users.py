"""
Script to create multiple users and admin accounts for testing purposes.
"""
import os
import sys
from datetime import datetime, timedelta
import random
from app import app, db
from models import User
from add_sample_data import create_sample_expenses

# List of regular users to create
USERS = [
    {"username": "john_doe", "email": "john@example.com"},
    {"username": "jane_smith", "email": "jane@example.com"},
    {"username": "mike_johnson", "email": "mike@example.com"},
    {"username": "sarah_williams", "email": "sarah@example.com"},
    {"username": "david_brown", "email": "david@example.com"},
    {"username": "emily_davis", "email": "emily@example.com"},
    {"username": "alex_wilson", "email": "alex@example.com"},
    {"username": "olivia_martinez", "email": "olivia@example.com"},
    {"username": "daniel_anderson", "email": "daniel@example.com"},
    {"username": "sophia_taylor", "email": "sophia@example.com"},
    {"username": "james_thomas", "email": "james@example.com"},
    {"username": "emma_jackson", "email": "emma@example.com"}
]

# List of admin users to create
ADMINS = [
    {"username": "admin_super", "email": "admin@example.com"},
    {"username": "admin_finance", "email": "finance@example.com"},
    {"username": "admin_system", "email": "system@example.com"}
]

def create_user(username, email, is_admin=False, password="Password123!"):
    """Create a user with the given details"""
    try:
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"User {username} or email {email} already exists. Skipping.")
            return existing_user
        
        # Create new user
        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        status = "admin" if is_admin else "regular"
        print(f"Created {status} user: {username} ({email}) with password: {password}")
        
        return user
    except Exception as e:
        print(f"Error creating user {username}: {str(e)}")
        db.session.rollback()
        return None

def main():
    """Main function to create users and sample data"""
    with app.app_context():
        print("Creating regular users...")
        for user_data in USERS:
            user = create_user(
                username=user_data["username"],
                email=user_data["email"]
            )
            
            if user:
                # Create sample expenses for each user (randomly between 10-30 expenses)
                num_expenses = random.randint(10, 30)
                create_sample_expenses(user.id, num_expenses)
                print(f"Created {num_expenses} sample expenses for {user.username}")
        
        print("\nCreating admin users...")
        for admin_data in ADMINS:
            create_user(
                username=admin_data["username"],
                email=admin_data["email"],
                is_admin=True
            )
        
        print("\nUser creation complete!")
        print(f"Created {len(USERS)} regular users and {len(ADMINS)} admin users.")
        print("All users have password: Password123!")

if __name__ == "__main__":
    main()