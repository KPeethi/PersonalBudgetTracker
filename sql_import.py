"""
SQL Data Import Utility for the Expense Tracker application.
Allows importing expense data directly from SQL files.
"""

import os
import logging
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from flask_login import current_user
from app import app, db
from models import Expense, ExcelImport

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_sql_file(file_path, params=None):
    """
    Execute a SQL file against the database.
    
    Args:
        file_path: Path to the SQL file
        params: Dict of parameters to pass to the SQL query
        
    Returns:
        tuple: (success, message) where success is a boolean and message contains execution details
    """
    try:
        with open(file_path, 'r') as f:
            sql_script = f.read()
        
        with app.app_context():
            db.session.execute(text(sql_script), params or {})
            db.session.commit()
        
        return True, "SQL script executed successfully"
    except Exception as e:
        logger.error(f"Error executing SQL file: {str(e)}")
        return False, f"Error executing SQL script: {str(e)}"

def import_expenses_from_sql(sql_query, user_id, import_description=None):
    """
    Import expenses from a SQL query.
    
    The SQL query should return rows with at least these columns:
        - date: Date of the expense
        - amount: Amount of the expense
        - category: Category of the expense
        - description: Description of the expense
    
    Optional columns:
        - payment_method: Payment method used
        - merchant: Merchant/vendor name
    
    Args:
        sql_query: SQL query to retrieve expense data
        user_id: ID of the user to associate the expenses with
        import_description: Optional description for the import
        
    Returns:
        tuple: (success, message, count) where success is a boolean, 
               message contains execution details, and count is the number of records imported
    """
    try:
        # Create an import record first
        excel_import = ExcelImport(
            user_id=user_id,
            filename="sql_import.sql",
            file_path="N/A (SQL Query)",
            file_size=0,
            description=import_description or "Imported from SQL query",
            status='processing'
        )
        
        with app.app_context():
            db.session.add(excel_import)
            db.session.commit()
            
            # Execute the query and fetch results
            result = db.session.execute(text(sql_query))
            
            # Get column names
            columns = result.keys()
            
            # Check required columns
            required_columns = ['date', 'amount', 'category', 'description']
            if not all(col in columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in columns]
                excel_import.status = 'failed'
                excel_import.error_message = f"Missing required columns: {', '.join(missing_cols)}"
                db.session.commit()
                return False, f"Missing required columns: {', '.join(missing_cols)}", 0
            
            # Process rows
            count = 0
            for row in result:
                try:
                    # Convert row to dict for easier access
                    row_dict = dict(zip(columns, row))
                    
                    # Handle date conversion
                    if isinstance(row_dict['date'], str):
                        try:
                            expense_date = datetime.strptime(row_dict['date'], '%Y-%m-%d').date()
                        except:
                            # Try other common date formats
                            date_formats = ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
                            for fmt in date_formats:
                                try:
                                    expense_date = datetime.strptime(row_dict['date'], fmt).date()
                                    break
                                except:
                                    continue
                            else:
                                # Skip if no format matches
                                continue
                    else:
                        # Assume it's already a date object
                        expense_date = row_dict['date']
                    
                    # Extract optional fields
                    payment_method = row_dict.get('payment_method') if 'payment_method' in row_dict else None
                    merchant = row_dict.get('merchant') if 'merchant' in row_dict else None
                    
                    # Create the expense
                    expense = Expense(
                        user_id=user_id,
                        date=expense_date,
                        amount=float(row_dict['amount']),
                        category=str(row_dict['category']),
                        description=str(row_dict['description']),
                        payment_method=payment_method,
                        merchant=merchant,
                        created_at=datetime.utcnow(),
                        excel_import_id=excel_import.id
                    )
                    db.session.add(expense)
                    count += 1
                except Exception as e:
                    logger.warning(f"Error processing row: {str(e)}")
                    continue
            
            # Commit all expense records
            db.session.commit()
            
            # Update import record
            excel_import.status = 'completed'
            excel_import.records_imported = count
            excel_import.completed_at = datetime.utcnow()
            db.session.commit()
            
            return True, f"Successfully imported {count} expense records", count
            
    except Exception as e:
        logger.error(f"Error importing expenses from SQL: {str(e)}")
        # Try to update the import record if it was created
        try:
            with app.app_context():
                excel_import.status = 'failed'
                excel_import.error_message = str(e)
                db.session.commit()
        except:
            pass
        return False, f"Error importing expenses from SQL: {str(e)}", 0

def import_expenses_from_sql_file(file_path, user_id, import_description=None):
    """
    Import expenses from a SQL file.
    
    The SQL file should contain a query that returns data with at least these columns:
        - date: Date of the expense
        - amount: Amount of the expense
        - category: Category of the expense
        - description: Description of the expense
    
    Optional columns:
        - payment_method: Payment method used
        - merchant: Merchant/vendor name
    
    Args:
        file_path: Path to the SQL file
        user_id: ID of the user to associate the expenses with
        import_description: Optional description for the import
        
    Returns:
        tuple: (success, message, count) where success is a boolean, 
               message contains execution details, and count is the number of records imported
    """
    try:
        # Read the SQL file
        with open(file_path, 'r') as f:
            sql_query = f.read()
        
        # Use the generic import function
        return import_expenses_from_sql(sql_query, user_id, import_description or f"Imported from {os.path.basename(file_path)}")
            
    except Exception as e:
        logger.error(f"Error importing expenses from SQL file: {str(e)}")
        return False, f"Error importing expenses from SQL file: {str(e)}", 0

def generate_sample_sql_import_file(output_path, dialect="postgresql"):
    """
    Generate a sample SQL file for importing expenses.
    
    Args:
        output_path: Path to save the SQL file
        dialect: SQL dialect to use (postgresql, mysql, or mssql)
        
    Returns:
        tuple: (success, message) where success is a boolean and message contains execution details
    """
    try:
        # Define the base query
        if dialect.lower() == "postgresql":
            sql = """
-- Sample expense data for import
-- This will return expense records in the format expected by the import utility
SELECT 
    '2025-04-01'::date as date,
    49.99 as amount,
    'Groceries' as category,
    'Weekly grocery shopping' as description,
    'Credit Card' as payment_method,
    'Local Supermarket' as merchant
UNION ALL SELECT 
    '2025-04-02'::date as date,
    12.50 as amount,
    'Transportation' as category,
    'Bus fare' as description,
    'Cash' as payment_method,
    'City Transit' as merchant
UNION ALL SELECT 
    '2025-04-03'::date as date,
    8.75 as amount,
    'Food & Dining' as category,
    'Lunch at cafe' as description,
    'Debit Card' as payment_method,
    'Corner Cafe' as merchant;
"""
        elif dialect.lower() == "mysql":
            sql = """
-- Sample expense data for import
-- This will return expense records in the format expected by the import utility
SELECT 
    STR_TO_DATE('2025-04-01', '%Y-%m-%d') as date,
    49.99 as amount,
    'Groceries' as category,
    'Weekly grocery shopping' as description,
    'Credit Card' as payment_method,
    'Local Supermarket' as merchant
UNION ALL SELECT 
    STR_TO_DATE('2025-04-02', '%Y-%m-%d') as date,
    12.50 as amount,
    'Transportation' as category,
    'Bus fare' as description,
    'Cash' as payment_method,
    'City Transit' as merchant
UNION ALL SELECT 
    STR_TO_DATE('2025-04-03', '%Y-%m-%d') as date,
    8.75 as amount,
    'Food & Dining' as category,
    'Lunch at cafe' as description,
    'Debit Card' as payment_method,
    'Corner Cafe' as merchant;
"""
        else:  # MSSQL
            sql = """
-- Sample expense data for import
-- This will return expense records in the format expected by the import utility
SELECT 
    CAST('2025-04-01' AS DATE) as date,
    49.99 as amount,
    'Groceries' as category,
    'Weekly grocery shopping' as description,
    'Credit Card' as payment_method,
    'Local Supermarket' as merchant
UNION ALL SELECT 
    CAST('2025-04-02' AS DATE) as date,
    12.50 as amount,
    'Transportation' as category,
    'Bus fare' as description,
    'Cash' as payment_method,
    'City Transit' as merchant
UNION ALL SELECT 
    CAST('2025-04-03' AS DATE) as date,
    8.75 as amount,
    'Food & Dining' as category,
    'Lunch at cafe' as description,
    'Debit Card' as payment_method,
    'Corner Cafe' as merchant;
"""
        
        # Write the SQL file
        with open(output_path, 'w') as f:
            f.write(sql)
        
        return True, f"Sample SQL import file generated at {output_path}"
    except Exception as e:
        logger.error(f"Error generating sample SQL import file: {str(e)}")
        return False, f"Error generating sample SQL import file: {str(e)}"

def import_expenses_from_database_table(table_name, db_url, user_id, import_description=None):
    """
    Import expenses from an external database table.
    
    Args:
        table_name: Name of the table to import data from
        db_url: Database URL to connect to
        user_id: ID of the user to associate the expenses with
        import_description: Optional description for the import
        
    Returns:
        tuple: (success, message, count) where success is a boolean, 
               message contains execution details, and count is the number of records imported
    """
    try:
        # Connect to the external database
        engine = create_engine(db_url)
        connection = engine.connect()
        
        # Query the table
        df = pd.read_sql_table(table_name, connection)
        
        # Close the connection
        connection.close()
        
        # Check required columns
        required_columns = ['date', 'amount', 'category', 'description']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            return False, f"Missing required columns in external table: {', '.join(missing_cols)}", 0
        
        # Create an import record
        excel_import = ExcelImport(
            user_id=user_id,
            filename=f"external_{table_name}.db",
            file_path=f"External DB: {table_name}",
            file_size=0,
            description=import_description or f"Imported from external database table: {table_name}",
            status='processing'
        )
        
        with app.app_context():
            db.session.add(excel_import)
            db.session.commit()
            
            # Process rows
            count = 0
            for _, row in df.iterrows():
                try:
                    # Handle date conversion
                    if isinstance(row['date'], str):
                        try:
                            expense_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                        except:
                            # Try other common date formats
                            date_formats = ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
                            for fmt in date_formats:
                                try:
                                    expense_date = datetime.strptime(row['date'], fmt).date()
                                    break
                                except:
                                    continue
                            else:
                                # Skip if no format matches
                                continue
                    else:
                        # Assume it's already a date object
                        expense_date = row['date']
                    
                    # Extract optional fields
                    payment_method = row.get('payment_method') if 'payment_method' in row and not pd.isna(row['payment_method']) else None
                    merchant = row.get('merchant') if 'merchant' in row and not pd.isna(row['merchant']) else None
                    
                    # Create the expense
                    expense = Expense(
                        user_id=user_id,
                        date=expense_date,
                        amount=float(row['amount']),
                        category=str(row['category']),
                        description=str(row['description']),
                        payment_method=payment_method,
                        merchant=merchant,
                        created_at=datetime.utcnow(),
                        excel_import_id=excel_import.id
                    )
                    db.session.add(expense)
                    count += 1
                except Exception as e:
                    logger.warning(f"Error processing row: {str(e)}")
                    continue
            
            # Commit all expense records
            db.session.commit()
            
            # Update import record
            excel_import.status = 'completed'
            excel_import.records_imported = count
            excel_import.completed_at = datetime.utcnow()
            db.session.commit()
            
            return True, f"Successfully imported {count} expense records from external database", count
            
    except Exception as e:
        logger.error(f"Error importing expenses from external database: {str(e)}")
        return False, f"Error importing expenses from external database: {str(e)}", 0

if __name__ == "__main__":
    # Generate a sample SQL import file for each supported dialect
    os.makedirs("static/templates", exist_ok=True)
    generate_sample_sql_import_file("static/templates/sample_import_postgresql.sql", "postgresql")
    generate_sample_sql_import_file("static/templates/sample_import_mysql.sql", "mysql")
    generate_sample_sql_import_file("static/templates/sample_import_mssql.sql", "mssql")
    
    print("Generated sample SQL import files in static/templates/")