"""
Script to check users in the expense tracker database.
"""

from app import app, db
from models import User

def check_users():
    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found in the database.")
        else:
            print(f"Found {len(users)} users:")
            for user in users:
                print(f"User: {user.username}, Email: {user.email}, Admin: {user.is_admin}")

if __name__ == "__main__":
    check_users()