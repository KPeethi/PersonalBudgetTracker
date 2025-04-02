"""
Models module for the Expense Tracker application.
Defines the data structures used in the application.
"""

from datetime import datetime
from app import db

class Expense(db.Model):
    """Represents an expense record in the system."""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.today)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        """String representation of an expense."""
        date_str = self.date.strftime('%Y-%m-%d')
        return f"Expense({date_str}, {self.description}, {self.category}, ${self.amount:.2f})"
