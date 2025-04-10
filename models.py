"""
Models module for the Expense Tracker application.
Defines the data structures used in the application.
"""

from datetime import datetime
import json
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

class UserPreference(db.Model):
    """Represents a user's preferences for app settings, notifications, etc."""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Theme preference (light, dark, system)
    theme = db.Column(db.String(20), default='light')
    
    # Notification Settings
    email_notifications = db.Column(db.Boolean, default=True)
    push_notifications = db.Column(db.Boolean, default=True)
    weekly_reports = db.Column(db.Boolean, default=True)
    monthly_reports = db.Column(db.Boolean, default=True)
    
    # Alert Settings
    alerts_enabled = db.Column(db.Boolean, default=True)
    alert_large_transactions = db.Column(db.Boolean, default=True)
    alert_low_balance = db.Column(db.Boolean, default=True)
    alert_upcoming_bills = db.Column(db.Boolean, default=True)
    alert_saving_goal_progress = db.Column(db.Boolean, default=True)
    alert_budget_exceeded = db.Column(db.Boolean, default=True)
    
    # Large transaction threshold
    large_transaction_threshold = db.Column(db.Float, default=100.0)
    
    # Other settings stored as JSON
    other_settings = db.Column(db.Text, default='{}')
    
    # Date fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('preferences', lazy=True, uselist=False))
    
    def get_other_settings(self):
        """Deserialize the other_settings JSON."""
        if not self.other_settings:
            return {}
        return json.loads(self.other_settings)
    
    def set_other_settings(self, settings_dict):
        """Serialize the other_settings to JSON."""
        self.other_settings = json.dumps(settings_dict)
    
    def __repr__(self):
        """String representation of user preferences."""
        return f"UserPreference(user_id={self.user_id}, theme={self.theme})"

class Budget(db.Model):
    """Represents a user's budget settings for different categories."""
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Monthly total budget
    total_budget = db.Column(db.Float, default=3000.0)
    
    # Category budgets
    food = db.Column(db.Float, default=500.0)  # Food & Dining
    transportation = db.Column(db.Float, default=300.0)
    entertainment = db.Column(db.Float, default=200.0)
    bills = db.Column(db.Float, default=800.0)  # Bills & Utilities
    shopping = db.Column(db.Float, default=400.0)
    other = db.Column(db.Float, default=800.0)
    
    # Date fields
    month = db.Column(db.Integer, default=lambda: datetime.utcnow().month)
    year = db.Column(db.Integer, default=lambda: datetime.utcnow().year)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('budgets', lazy=True))
    
    def __repr__(self):
        """String representation of a budget."""
        return f"Budget(user_id={self.user_id}, total=${self.total_budget:.2f}, month={self.month}/{self.year})"

class UserNotification(db.Model):
    """Represents notifications for users."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')  # info, warning, danger, success
    is_read = db.Column(db.Boolean, default=False)
    
    # Related IDs (e.g., expense_id if notification is about an expense)
    related_id = db.Column(db.Integer, nullable=True)
    related_type = db.Column(db.String(50), nullable=True)
    
    # Date fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    
    def __repr__(self):
        """String representation of a notification."""
        return f"UserNotification(title={self.title}, type={self.notification_type}, read={self.is_read})"
