"""
Script to reset passwords for admin users to a known value.
"""
from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import argparse

def reset_admin_passwords(verbose=False):
    """Reset passwords for admin users."""
    with app.app_context():
        # Find admin users
        admin_users = User.query.filter_by(is_admin=True).all()
        
        if verbose:
            print(f"Found {len(admin_users)} admin users")
        
        # Standard test password
        new_password = "Password123!"
        new_hash = generate_password_hash(new_password)
        
        # Update passwords
        for user in admin_users:
            if verbose:
                print(f"Resetting password for admin: {user.username} ({user.email})")
            user.password_hash = new_hash
        
        # Commit changes
        db.session.commit()
        
        if verbose:
            print("Passwords reset successfully!")
            print(f"New password for all admin users: {new_password}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset admin passwords")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    reset_admin_passwords(verbose=args.verbose)