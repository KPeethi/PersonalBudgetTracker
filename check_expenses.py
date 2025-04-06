"""
Script to check expenses in the expense tracker database.
"""

from app import app, db
from models import User, Expense
from datetime import datetime, timedelta

def check_expenses():
    with app.app_context():
        # Get total count of expenses
        total_expenses = Expense.query.count()
        print(f"Total expenses in database: {total_expenses}")
        
        # Check expenses by user
        users = User.query.all()
        
        for user in users:
            user_expenses = Expense.query.filter_by(user_id=user.id).count()
            
            # Check expenses for the current month
            today = datetime.today()
            first_day_current_month = datetime(today.year, today.month, 1).date()
            current_month_expenses = Expense.query.filter_by(user_id=user.id).filter(
                Expense.date >= first_day_current_month
            ).count()
            
            # Check expenses for the previous month
            if today.month == 1:
                prev_month = 12
                prev_year = today.year - 1
            else:
                prev_month = today.month - 1
                prev_year = today.year
                
            first_day_prev_month = datetime(prev_year, prev_month, 1).date()
            
            if prev_month == 12:
                next_month = 1
                next_year = prev_year + 1
            else:
                next_month = prev_month + 1
                next_year = prev_year
                
            first_day_next_month = datetime(next_year, next_month, 1).date()
            prev_month_expenses = Expense.query.filter_by(user_id=user.id).filter(
                Expense.date >= first_day_prev_month,
                Expense.date < first_day_next_month
            ).count()
            
            print(f"User: {user.username} - Total: {user_expenses}, Current Month: {current_month_expenses}, Previous Month: {prev_month_expenses}")

if __name__ == "__main__":
    check_expenses()