"""
Script to create a test admin user account.
"""
from app import app, db
from models import User
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin():
    with app.app_context():
        # Check if admin user already exists
        admin = User.query.filter_by(email='admin@example.com').first()
        
        if not admin:
            # Create a new admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('Password123!'),
                is_admin=True,
                last_login=datetime.utcnow(),
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print('Admin user created successfully!')
        else:
            print('Admin user already exists.')
            
        # List all users
        all_users = User.query.all()
        print(f'Total users: {len(all_users)}')
        for user in all_users[:5]:
            print(f'User: {user.username}, Email: {user.email}, Is Admin: {user.is_admin}')

if __name__ == '__main__':
    create_admin()