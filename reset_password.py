"""
Script to reset a user's password in the expense tracker database.
"""
import sys
from werkzeug.security import generate_password_hash
from main import app, db
from models import User

def reset_password(email, new_password):
    """Reset a user's password"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Error: No user found with email {email}")
            return False
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"Password reset successfully for user: {user.username} ({email})")
        return True

def create_test_user(email, username, password, is_admin=False, is_business_user=False):
    """Create a new test user if they don't exist"""
    with app.app_context():
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"User {email} already exists, updating password")
            existing_user.password_hash = generate_password_hash(password)
            existing_user.is_admin = is_admin
            existing_user.is_business_user = is_business_user
            db.session.commit()
            print(f"Updated user: {username} ({email}), Admin: {is_admin}, Business: {is_business_user}")
            return existing_user
        
        new_user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            is_admin=is_admin,
            is_business_user=is_business_user,
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()
        print(f"Created new user: {username} ({email}), Admin: {is_admin}, Business: {is_business_user}")
        return new_user

if __name__ == "__main__":
    # Create or update test accounts with simple passwords
    create_test_user("test.regular@example.com", "test_regular", "test123", is_admin=False, is_business_user=False)
    create_test_user("test.business@example.com", "test_business", "test123", is_admin=False, is_business_user=True)
    create_test_user("test.admin@example.com", "test_admin", "test123", is_admin=True, is_business_user=False)
    
    # Reset password for specific user if provided
    if len(sys.argv) > 2:
        email = sys.argv[1]
        new_password = sys.argv[2]
        reset_password(email, new_password)