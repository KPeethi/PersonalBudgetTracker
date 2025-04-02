"""
Database module for the Expense Tracker application.
Handles connections and operations with Microsoft SQL Server.
"""

import os
import logging
import datetime
import pyodbc
from typing import List, Dict, Any, Optional
from models import Expense

# Set up logging
logger = logging.getLogger(__name__)

# Database connection settings
SERVER = os.getenv("DB_SERVER", "localhost")
DATABASE = os.getenv("DB_NAME", "ExpenseTracker")
USERNAME = os.getenv("DB_USER", "sa")
PASSWORD = os.getenv("DB_PASSWORD", "")
DRIVER = os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}")

# Connection string for MSSQL
CONNECTION_STRING = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}"

def get_connection():
    """Create and return a connection to the database."""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def initialize_db():
    """Initialize the database, creating the table if it doesn't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create the Expenses table if it doesn't exist
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Expenses' AND xtype='U')
        CREATE TABLE Expenses (
            Id INT PRIMARY KEY IDENTITY(1,1),
            Date DATE,
            Description NVARCHAR(255),
            Category NVARCHAR(100),
            Amount DECIMAL(10,2)
        )
        """)
        
        conn.commit()
        logger.info("Database initialized successfully")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def add_expense(expense: Expense) -> bool:
    """
    Add a new expense to the database.
    
    Args:
        expense: An Expense object containing the expense details
        
    Returns:
        True if the expense was added successfully, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO Expenses (Date, Description, Category, Amount)
        VALUES (?, ?, ?, ?)
        """, 
        expense.date, expense.description, expense.category, expense.amount)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Added expense: {expense}")
        return True
    except Exception as e:
        logger.error(f"Error adding expense: {e}")
        raise

def get_all_expenses() -> List[Dict[str, Any]]:
    """
    Retrieve all expenses from the database, sorted by date (most recent first).
    
    Returns:
        A list of dictionaries containing expense details
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT Id, Date, Description, Category, Amount
        FROM Expenses
        ORDER BY Date DESC
        """)
        
        # Convert rows to dictionaries
        expenses = []
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            expense_dict = dict(zip(columns, row))
            expenses.append(expense_dict)
            
        cursor.close()
        conn.close()
        return expenses
    except Exception as e:
        logger.error(f"Error retrieving expenses: {e}")
        raise

def get_expenses_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Retrieve expenses filtered by category.
    
    Args:
        category: The category to filter by
        
    Returns:
        A list of dictionaries containing expense details
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT Id, Date, Description, Category, Amount
        FROM Expenses
        WHERE Category = ?
        ORDER BY Date DESC
        """, category)
        
        # Convert rows to dictionaries
        expenses = []
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            expense_dict = dict(zip(columns, row))
            expenses.append(expense_dict)
            
        cursor.close()
        conn.close()
        return expenses
    except Exception as e:
        logger.error(f"Error retrieving expenses by category: {e}")
        raise

def get_categories() -> List[str]:
    """
    Retrieve all unique categories from the database.
    
    Returns:
        A list of category strings
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT DISTINCT Category
        FROM Expenses
        ORDER BY Category
        """)
        
        categories = [row[0] for row in cursor.fetchall()]
            
        cursor.close()
        conn.close()
        return categories
    except Exception as e:
        logger.error(f"Error retrieving categories: {e}")
        raise

def get_monthly_summary() -> List[Dict[str, Any]]:
    """
    Retrieve a summary of expenses grouped by month and year.
    
    Returns:
        A list of dictionaries containing monthly summaries
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            MONTH(Date) as month,
            YEAR(Date) as year,
            SUM(Amount) as total_amount
        FROM Expenses
        GROUP BY YEAR(Date), MONTH(Date)
        ORDER BY year DESC, month DESC
        """)
        
        # Convert rows to dictionaries
        summaries = []
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            summary_dict = dict(zip(columns, row))
            summaries.append(summary_dict)
            
        cursor.close()
        conn.close()
        return summaries
    except Exception as e:
        logger.error(f"Error retrieving monthly summary: {e}")
        raise

def delete_expense(expense_id: int) -> bool:
    """
    Delete an expense by ID.
    
    Args:
        expense_id: The ID of the expense to delete
        
    Returns:
        True if the expense was deleted successfully, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Expenses WHERE Id = ?", expense_id)
        
        affected_rows = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            logger.info(f"Deleted expense with ID: {expense_id}")
            return True
        else:
            logger.warning(f"No expense found with ID: {expense_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting expense: {e}")
        raise

def get_expense_by_id(expense_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve an expense by ID.
    
    Args:
        expense_id: The ID of the expense to retrieve
        
    Returns:
        A dictionary containing the expense details, or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT Id, Date, Description, Category, Amount
        FROM Expenses
        WHERE Id = ?
        """, expense_id)
        
        row = cursor.fetchone()
        
        if row:
            columns = [column[0] for column in cursor.description]
            expense_dict = dict(zip(columns, row))
            cursor.close()
            conn.close()
            return expense_dict
        else:
            cursor.close()
            conn.close()
            return None
    except Exception as e:
        logger.error(f"Error retrieving expense by ID: {e}")
        raise
