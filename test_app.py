"""
Test version of the Budget AI application without login requirements.
This version allows testing without needing to authenticate.
WARNING: Do not use in production environments!
"""

import os
import sys
from flask import render_template, request, redirect, url_for, flash
from functools import wraps
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the main application
try:
    from app import app, db
    from models import User, Expense
    from main import UPLOAD_FOLDER, EXCEL_UPLOAD_FOLDER, TEMPLATES_FOLDER, TEMP_CHARTS_FOLDER
    import visualization
except ImportError as e:
    logger.error(f"Error importing application: {e}")
    sys.exit(1)

# Create upload directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXCEL_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)
os.makedirs(TEMP_CHARTS_FOLDER, exist_ok=True)

# Create a test user in session without login
@app.before_request
def create_test_user():
    """Create a test user in the session without requiring login"""
    # Skip for static files and login routes
    if request.path.startswith('/static') or request.path in ['/login', '/register', '/logout']:
        return
    
    # Check if we need to create a test user
    try:
        # Look for a test user in the database
        test_user = User.query.filter_by(email='test@example.com').first()
        if not test_user:
            # Create a test user if it doesn't exist
            logger.info("Creating test user in the database")
            test_user = User(
                username='tester',
                email='test@example.com',
                is_admin=True,
                is_business_user=True
            )
            test_user.set_password('password123')
            db.session.add(test_user)
            db.session.commit()
            logger.info(f"Test user created with ID: {test_user.id}")
    except Exception as e:
        logger.error(f"Error creating test user: {e}")

# Replace login_required decorator with a dummy version that always allows access
def dummy_login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        return func(*args, **kwargs)
    return decorated_view

# Override login_required decorator in routes
import main
import flask_login
# Store the original decorator
original_login_required = flask_login.login_required
# Replace with dummy decorator
flask_login.login_required = dummy_login_required

# Override current_user to always return our test user
class DummyUser:
    def __init__(self):
        # Look up the test user
        self.test_user = User.query.filter_by(email='test@example.com').first()
        if self.test_user:
            self._id = self.test_user.id
            self.id = self.test_user.id
            self.username = self.test_user.username
            self.email = self.test_user.email
            self.is_admin = self.test_user.is_admin
            self.is_business_user = self.test_user.is_business_user
            self.is_authenticated = True
            self.is_active = True
            self.is_anonymous = False
            self.is_suspended = False
            self.suspension_reason = None

    def get_id(self):
        return str(self._id)
        
# Create a dummy current_user
dummy_user = DummyUser()

# Create a simple test homepage that redirects to the main app
@app.route('/test')
def test_homepage():
    """Test homepage that allows navigation to the main application without login"""
    return render_template('test_home.html', 
                           title='Test Mode',
                           user=dummy_user)

# Create a handler to inject our dummy user
@app.context_processor
def inject_test_user():
    """Make the test user available to all templates"""
    return dict(current_user=dummy_user)

# Create a welcome page for test mode
@app.route('/welcome')
def welcome():
    """Welcome page for test mode"""
    return render_template('welcome.html', 
                           title='Welcome to Test Mode', 
                           user=dummy_user)

# Optional: Add test data if needed
def add_test_data():
    """Add sample test data to the database"""
    try:
        # Check if we already have test data
        if Expense.query.filter_by(user_id=dummy_user.id).count() > 0:
            return
        
        # Add some sample expenses
        test_expenses = [
            Expense(
                date=datetime(2025, 3, 15),
                description="Test Groceries",
                category="Food",
                amount=75.25,
                user_id=dummy_user.id
            ),
            Expense(
                date=datetime(2025, 3, 18),
                description="Test Utilities",
                category="Bills",
                amount=120.50,
                user_id=dummy_user.id
            ),
            Expense(
                date=datetime(2025, 3, 20),
                description="Test Restaurant",
                category="Food",
                amount=45.80,
                user_id=dummy_user.id
            ),
            Expense(
                date=datetime(2025, 3, 22),
                description="Test Entertainment",
                category="Entertainment",
                amount=25.00,
                user_id=dummy_user.id
            ),
            Expense(
                date=datetime(2025, 3, 25),
                description="Test Clothing",
                category="Shopping",
                amount=89.99,
                user_id=dummy_user.id
            )
        ]
        
        for expense in test_expenses:
            db.session.add(expense)
        
        db.session.commit()
        logger.info(f"Added {len(test_expenses)} test expenses to the database")
    except Exception as e:
        logger.error(f"Error adding test data: {e}")
        db.session.rollback()

# Add test data when the app starts
with app.app_context():
    add_test_data()

if __name__ == "__main__":
    logger.info("Starting Budget AI in TEST MODE")
    logger.warning("This mode bypasses authentication and is not secure!")
    logger.warning("Do NOT use this in production environments!")
    app.run(host="0.0.0.0", port=5001, debug=True)