"""
Excel data processor for the Expense Tracker application.
Handles the import of expense data from Excel/CSV files.
"""

import os
import pandas as pd
import logging
from datetime import datetime
from app import db, app
from models import ExcelImport, Expense
from sqlalchemy import create_engine, text
from flask_login import current_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_excel_import(import_id):
    """
    Process an Excel import by reading the file and creating expense records.
    
    Args:
        import_id: The ID of the ExcelImport record to process
        
    Returns:
        bool: True if the import was processed successfully, False otherwise
    """
    with app.app_context():
        try:
            # Get the import record
            excel_import = ExcelImport.query.get(import_id)
            if not excel_import:
                logger.error(f"ExcelImport record with ID {import_id} not found")
                return False
            
            # Update status to processing
            excel_import.status = 'processing'
            db.session.commit()
            
            # Check if file exists
            if not os.path.exists(excel_import.file_path):
                excel_import.status = 'failed'
                excel_import.error_message = f"File {excel_import.file_path} does not exist"
                db.session.commit()
                logger.error(f"File not found: {excel_import.file_path}")
                return False
            
            # Read the file
            try:
                file_ext = os.path.splitext(excel_import.filename)[1].lower()
                if file_ext == '.csv':
                    df = pd.read_csv(excel_import.file_path)
                else:  # Excel formats (.xlsx, .xls)
                    df = pd.read_excel(excel_import.file_path)
            except Exception as e:
                excel_import.status = 'failed'
                excel_import.error_message = f"Error reading file: {str(e)}"
                db.session.commit()
                logger.error(f"Error reading file {excel_import.file_path}: {str(e)}")
                return False
            
            # Validate and process the data
            required_columns = ['date', 'amount', 'category', 'description']
            if not all(col in df.columns for col in required_columns):
                missing_cols = [col for col in required_columns if col not in df.columns]
                excel_import.status = 'failed'
                excel_import.error_message = f"Missing required columns: {', '.join(missing_cols)}"
                db.session.commit()
                logger.error(f"Missing required columns in file {excel_import.file_path}: {missing_cols}")
                return False
            
            # Process rows
            num_rows = 0
            for _, row in df.iterrows():
                try:
                    # Skip rows with NaN values in required fields
                    if any(pd.isna(row[col]) for col in required_columns):
                        continue
                    
                    # Create expense record
                    try:
                        expense_date = pd.to_datetime(row['date']).date()
                    except:
                        # Try to parse the date as string
                        try:
                            expense_date = datetime.strptime(str(row['date']), '%Y-%m-%d').date()
                        except:
                            # Skip rows with invalid dates
                            continue
                    
                    # Extract optional fields
                    payment_method = row.get('payment_method', None) if 'payment_method' in row and not pd.isna(row['payment_method']) else None
                    merchant = row.get('merchant', None) if 'merchant' in row and not pd.isna(row['merchant']) else None
                    
                    # Create the expense
                    expense = Expense(
                        user_id=excel_import.user_id,
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
                    num_rows += 1
                except Exception as e:
                    logger.warning(f"Error processing row: {str(e)}")
                    continue
            
            # Commit all expense records
            db.session.commit()
            
            # Update import record
            excel_import.status = 'completed'
            excel_import.num_rows = num_rows
            excel_import.processed_date = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Successfully processed {num_rows} rows from file {excel_import.filename}")
            return True
            
        except Exception as e:
            db.session.rollback()
            try:
                excel_import = ExcelImport.query.get(import_id)
                if excel_import:
                    excel_import.status = 'failed'
                    excel_import.error_message = str(e)
                    db.session.commit()
            except:
                logger.error("Failed to update import status")
                
            logger.error(f"Error processing Excel import {import_id}: {str(e)}")
            return False

def process_pending_imports():
    """
    Process all pending imports in the database.
    
    Returns:
        int: Number of imports processed
    """
    with app.app_context():
        try:
            # Get all pending imports
            pending_imports = ExcelImport.query.filter_by(status='pending').all()
            
            count = 0
            for excel_import in pending_imports:
                if process_excel_import(excel_import.id):
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error processing pending imports: {str(e)}")
            return 0

if __name__ == "__main__":
    # When run directly, process all pending imports
    count = process_pending_imports()
    logger.info(f"Processed {count} pending imports")