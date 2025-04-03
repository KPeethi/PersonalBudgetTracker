from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_admin_user(username, email, password):
    """Create an admin user"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists")
            return
        
        # Create new admin user
        admin_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True
        )
        
        # Add to database
        db.session.add(admin_user)
        db.session.commit()
        print(f"Created admin user: {username} with email: {email}")

if __name__ == "__main__":
    # Create admin user with credentials
    admin_username = "admin"
    admin_email = "admin@example.com"
    admin_password = "Admin123!"
    
    create_admin_user(admin_username, admin_email, admin_password)
    print("\nAdmin login credentials:")
    print(f"Email: {admin_email}")
    print(f"Password: {admin_password}")