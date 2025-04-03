"""
Models module for the Expense Tracker application.
Defines the data structures used in the application.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    """Represents a standard user in the system."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_suspended = db.Column(db.Boolean, default=False)
    suspension_reason = db.Column(db.String(255), nullable=True)
    
    # Relationship with expenses
    expenses = db.relationship('Expense', backref='user', lazy=True)
    
    def set_password(self, password):
        """Generate password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password hash."""
        import logging
        logger = logging.getLogger(__name__)
        result = check_password_hash(self.password_hash, password)
        logger.debug(f"Password check for user {self.username}: {'passed' if result else 'failed'}")
        return result
    
    def __repr__(self):
        """String representation of a user."""
        return f"User({self.username}, {self.email})"

class Expense(db.Model):
    """Represents an expense record in the system."""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.today)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        """String representation of an expense."""
        date_str = self.date.strftime('%Y-%m-%d')
        return f"Expense({date_str}, {self.description}, {self.category}, ${self.amount:.2f})"
