#!/usr/bin/env python3
"""
Expense Tracker CLI Application
------------------------------
A command-line tool to track personal expenses using Python and PostgreSQL.
"""

import os
import sys
import datetime
from typing import Any, List, Dict, Optional, Callable
from app import app, db
from models import Expense

def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_menu() -> None:
    """Display the main menu options."""
    print("\n===== EXPENSE TRACKER =====")
    print("1. Add Expense")
    print("2. View All Expenses")
    print("3. View Expenses by Category")
    print("4. View Monthly Summary")
    print("5. Exit")
    print("===========================")

def get_input(prompt: str, input_type: type = str, 
              validator: Optional[Callable] = None, 
              error_msg: str = "Invalid input. Please try again.") -> Any:
    """
    Get and validate user input.
    
    Args:
        prompt: The prompt to display to the user
        input_type: The expected type of the input
        validator: A function that validates the input
        error_msg: Message to display if validation fails
        
    Returns:
        The validated input
    """
    while True:
        try:
            user_input = input(prompt)
            
            # Special case for date input
            if input_type == datetime.date and user_input.lower() == 'today':
                return datetime.datetime.today().date()
            
            # Convert input to the expected type
            converted_input = input_type(user_input)
            
            # Validate the input if a validator is provided
            if validator and not validator(converted_input):
                print(error_msg)
                continue
                
            return converted_input
        except ValueError:
            print(f"Error: Please enter a valid {input_type.__name__}.")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return None

def validate_amount(amount: float) -> bool:
    """Validate that amount is positive."""
    return amount > 0

def validate_category(category: str) -> bool:
    """Validate that category is not empty."""
    return bool(category.strip())

def validate_description(description: str) -> bool:
    """Validate that description is not empty."""
    return bool(description.strip())

def add_expense() -> None:
    """Add a new expense to the database."""
    print("\n----- Add New Expense -----")
    
    date_input = get_input("Date (YYYY-MM-DD or 'today'): ", datetime.date)
    if date_input is None:
        return
    
    description = get_input("Description: ", str, validate_description, 
                            "Description cannot be empty.")
    if description is None:
        return
    
    category = get_input("Category: ", str, validate_category, 
                         "Category cannot be empty.")
    if category is None:
        return
    
    amount = get_input("Amount ($): ", float, validate_amount, 
                       "Amount must be greater than 0.")
    if amount is None:
        return
    
    try:
        # Create a new Expense object and add it to the database
        with app.app_context():
            expense = Expense(
                date=date_input,
                description=description,
                category=category,
                amount=amount
            )
            db.session.add(expense)
            db.session.commit()
        print("\nExpense added successfully!")
    except Exception as e:
        print(f"\nError adding expense: {str(e)}")

def view_all_expenses() -> None:
    """View all expenses sorted by date (most recent first)."""
    print("\n----- All Expenses -----")
    
    try:
        with app.app_context():
            expenses = Expense.query.order_by(Expense.date.desc()).all()
            display_expenses(expenses)
    except Exception as e:
        print(f"Error retrieving expenses: {str(e)}")

def view_expenses_by_category() -> None:
    """View expenses filtered by category."""
    with app.app_context():
        # Get all unique categories
        categories = db.session.query(Expense.category).distinct().order_by(Expense.category).all()
        category_list = [cat[0] for cat in categories]
    
    if not category_list:
        print("\nNo categories found.")
        return
    
    print("\n----- Categories -----")
    for i, category in enumerate(category_list, 1):
        print(f"{i}. {category}")
    
    selection = get_input("\nSelect a category (number): ", int)
    if selection is None or selection < 1 or selection > len(category_list):
        print("Invalid selection.")
        return
    
    selected_category = category_list[selection - 1]
    print(f"\n----- Expenses in '{selected_category}' -----")
    
    try:
        with app.app_context():
            expenses = Expense.query.filter_by(category=selected_category).order_by(Expense.date.desc()).all()
            display_expenses(expenses)
    except Exception as e:
        print(f"Error retrieving expenses: {str(e)}")

def view_monthly_summary() -> None:
    """View a summary of expenses by month."""
    print("\n----- Monthly Summary -----")
    
    try:
        with app.app_context():
            # Get monthly summary data
            monthly_data = db.session.query(
                db.func.extract('month', Expense.date).label('month'),
                db.func.extract('year', Expense.date).label('year'),
                db.func.sum(Expense.amount).label('total_amount')
            ).group_by(
                db.func.extract('year', Expense.date),
                db.func.extract('month', Expense.date)
            ).order_by(
                db.func.extract('year', Expense.date).desc(),
                db.func.extract('month', Expense.date).desc()
            ).all()
            
            if not monthly_data:
                print("No expense data available.")
                return
            
            # Format and display the monthly summary
            print("\nMonth       Year    Total Amount")
            print("--------------------------------")
            grand_total = 0
            
            for month_num, year, total in monthly_data:
                month_name = datetime.datetime(int(year), int(month_num), 1).strftime('%B')
                print(f"{month_name:<12} {int(year):<6} ${float(total):.2f}")
                grand_total += float(total)
            
            print("--------------------------------")
            print(f"Grand Total:          ${grand_total:.2f}")
            
    except Exception as e:
        print(f"Error retrieving monthly summary: {str(e)}")

def display_expenses(expenses: List[Expense]) -> None:
    """Display a formatted table of expenses."""
    if not expenses:
        print("No expenses found.")
        return
    
    # Calculate the total
    total = sum(expense.amount for expense in expenses)
    
    # Print the header
    print("\nDate       Description                Category     Amount")
    print("-----------------------------------------------------------")
    
    # Print each expense
    for expense in expenses:
        date_str = expense.date.strftime('%Y-%m-%d')
        print(f"{date_str} {expense.description[:25]:<25} {expense.category:<12} ${expense.amount:.2f}")
    
    # Print the total
    print("-----------------------------------------------------------")
    print(f"Total:                                         ${total:.2f}")

def main() -> None:
    """Main application entry point."""
    while True:
        clear_screen()
        display_menu()
        
        choice = get_input("\nEnter your choice (1-5): ", int)
        if choice is None:
            continue
        
        if choice == 1:
            add_expense()
        elif choice == 2:
            view_all_expenses()
        elif choice == 3:
            view_expenses_by_category()
        elif choice == 4:
            view_monthly_summary()
        elif choice == 5:
            print("\nThank you for using Expense Tracker! Goodbye.")
            sys.exit(0)
        else:
            print("\nInvalid choice. Please select a number between 1 and 5.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()