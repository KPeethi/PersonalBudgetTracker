"""
Script to add sample data to the expense tracker database.
This provides some initial data to demonstrate the application's functionality.
"""

import random
from datetime import datetime, timedelta
from app import app, db
from models import User, Expense

def create_sample_expenses(user_id, num_expenses=20):
    """
    Create sample expenses for a given user.
    
    Args:
        user_id: The ID of the user to create expenses for
        num_expenses: Number of sample expenses to create
    """
    categories = [
        "Groceries", "Dining", "Transportation", "Entertainment", 
        "Utilities", "Housing", "Healthcare", "Education", 
        "Shopping", "Travel", "Subscriptions", "Gifts"
    ]
    
    descriptions = {
        "Groceries": ["Supermarket", "Farmer's Market", "Convenience Store", "Organic Shop"],
        "Dining": ["Restaurant", "Cafe", "Fast Food", "Food Delivery"],
        "Transportation": ["Gas", "Public Transit", "Ride Share", "Car Maintenance"],
        "Entertainment": ["Movies", "Concert", "Streaming Service", "Games"],
        "Utilities": ["Electricity", "Water", "Internet", "Phone"],
        "Housing": ["Rent", "Mortgage", "Home Insurance", "Repairs"],
        "Healthcare": ["Doctor Visit", "Pharmacy", "Health Insurance", "Fitness"],
        "Education": ["Books", "Tuition", "Online Course", "School Supplies"],
        "Shopping": ["Clothing", "Electronics", "Home Goods", "Personal Care"],
        "Travel": ["Flights", "Hotel", "Car Rental", "Vacation Activities"],
        "Subscriptions": ["Software", "Magazine", "Membership", "Digital Service"],
        "Gifts": ["Birthday Gift", "Holiday Gift", "Donation", "Charity"]
    }
    
    # Create expenses over the last 3 months
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    expenses = []
    for _ in range(num_expenses):
        # Random date within the last 3 months
        days_back = random.randint(0, 90)
        expense_date = end_date - timedelta(days=days_back)
        
        # Random category and description
        category = random.choice(categories)
        description = f"{random.choice(descriptions[category])}"
        
        # Random amount between $5 and $200
        amount = round(random.uniform(5, 200), 2)
        
        expense = Expense(
            date=expense_date,
            description=description,
            category=category,
            amount=amount,
            user_id=user_id
        )
        expenses.append(expense)
    
    return expenses

def main():
    with app.app_context():
        # Get all users
        users = User.query.all()
        
        if not users:
            print("No users found! Make sure to create users first.")
            return
        
        total_added = 0
        
        for user in users:
            # Force create sample expenses for all users
            print(f"Creating sample expenses for user: {user.username}...")
            sample_expenses = create_sample_expenses(user.id, num_expenses=30)
            
            # Add expenses to database
            for expense in sample_expenses:
                db.session.add(expense)
            
            total_added += len(sample_expenses)
        
        # Commit changes
        db.session.commit()
        print(f"Added {total_added} sample expenses successfully!")

if __name__ == "__main__":
    main()