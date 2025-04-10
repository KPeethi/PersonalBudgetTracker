"""
Script to reset the admin user password.
"""
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def reset_admin_password():
    with app.app_context():
        # Find the admin user
        admin = User.query.filter_by(email='admin@example.com').first()
        
        if admin:
            # Reset password
            admin.password_hash = generate_password_hash('Admin123!')
            db.session.commit()
            print(f'Password reset for admin user: {admin.email}')
            print('New password: Admin123!')
        else:
            print('Admin user not found!')

if __name__ == '__main__':
    reset_admin_password()