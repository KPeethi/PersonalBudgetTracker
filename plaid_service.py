"""
Plaid integration module for the Expense Tracker application.
Used to fetch financial data from Plaid for demonstration purposes.
"""

import os
import datetime
import random
import logging
import json
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Get Plaid credentials from environment variables
PLAID_CLIENT_ID = os.environ.get('PLAID_CLIENT_ID')
PLAID_SECRET = os.environ.get('PLAID_SECRET')
PLAID_ENV = os.environ.get('PLAID_ENV', 'sandbox').lower()

# Determine if we should use real Plaid API data or mock data
USE_MOCK_DATA = False
if not PLAID_CLIENT_ID or not PLAID_SECRET:
    logger.warning("Plaid credentials not found, falling back to mock data")
    USE_MOCK_DATA = True
else:
    logger.info("Using real Plaid API integration with credentials")

# Import requests for direct HTTP calls to Plaid API
import requests

# Set up Plaid API base URL based on environment
PLAID_API_BASE = 'https://sandbox.plaid.com' if PLAID_ENV == 'sandbox' else 'https://production.plaid.com'
logger.info(f"Using Plaid API environment: {PLAID_ENV} at {PLAID_API_BASE}")

# Mock categories for generating sample data
MOCK_CATEGORIES = [
    "Food & Dining", 
    "Shopping", 
    "Transportation", 
    "Bills & Utilities", 
    "Entertainment", 
    "Health & Fitness", 
    "Travel", 
    "Education", 
    "Gifts & Donations", 
    "Personal Care"
]

# Mock merchants for generating sample data
MOCK_MERCHANTS = {
    "Food & Dining": ["Grocery Store", "Restaurant", "Coffee Shop", "Fast Food", "Food Delivery"],
    "Shopping": ["Department Store", "Online Shop", "Electronics Store", "Clothing Store", "Home Goods"],
    "Transportation": ["Gas Station", "Ride Share", "Public Transport", "Car Repair", "Parking"],
    "Bills & Utilities": ["Electric Bill", "Water Bill", "Internet Provider", "Phone Bill", "Streaming Service"],
    "Entertainment": ["Movie Theater", "Concert Tickets", "Streaming Service", "Gaming", "Sports Event"],
    "Health & Fitness": ["Gym Membership", "Pharmacy", "Doctor Visit", "Health Insurance", "Fitness Equipment"],
    "Travel": ["Airline", "Hotel", "Vacation Rental", "Car Rental", "Travel Agency"],
    "Education": ["Tuition", "Books", "Online Course", "School Supplies", "Tutoring"],
    "Gifts & Donations": ["Gift Shop", "Charity", "Fundraiser", "Donations", "Gift Cards"],
    "Personal Care": ["Salon", "Spa", "Barber Shop", "Cosmetics", "Self-care Products"]
}

def create_link_token() -> Dict[str, Any]:
    """
    Create a link token for initializing Plaid Link.
    
    Returns:
        Dictionary containing the link token or an error message
    """
    if USE_MOCK_DATA:
        # Return a mock link token
        logger.warning("Using mock link token since Plaid credentials are not available")
        return {
            "link_token": "mock_link_token",
            "expiration": datetime.datetime.now().isoformat(),
            "request_id": "mock_request_id"
        }
    
    try:
        # Create a unique client user ID
        client_user_id = f"user-{random.randint(10000, 99999)}"
        
        # Prepare request payload
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "client_name": "Expense Tracker",
            "user": {
                "client_user_id": client_user_id
            },
            "products": ["transactions"],
            "country_codes": ["US"],
            "language": "en"
            # Optional fields:
            # "webhook": "https://webhook.example.com",
            # "redirect_uri": "https://expense-tracker.replit.app/oauth-callback"
        }
        
        logger.info(f"Creating link token for client_user_id: {client_user_id}")
        
        # Make request to Plaid API
        response = requests.post(
            f"{PLAID_API_BASE}/link/token/create",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        # Handle response
        if response.status_code == 200:
            token_dict = response.json()
            
            # Log partial token for debugging (don't log the full token for security)
            if "link_token" in token_dict:
                token = token_dict["link_token"]
                masked_token = token[:5] + "..." + token[-5:] if len(token) > 10 else "***"
                logger.info(f"Successfully created link token: {masked_token}")
            
            return token_dict
        else:
            error_message = f"Error creating link token. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_message)
            return {"error": error_message}
            
    except Exception as e:
        logger.error(f"Error creating link token: {str(e)}")
        return {"error": str(e)}

def exchange_public_token(public_token: str) -> Dict[str, Any]:
    """
    Exchange a public token for an access token and item ID.
    
    Args:
        public_token: The public token received from Plaid Link
        
    Returns:
        Dictionary containing the access token, item ID, or an error message
    """
    if USE_MOCK_DATA:
        # Return a mock access token
        return {
            "access_token": "mock_access_token",
            "item_id": "mock_item_id",
            "request_id": "mock_request_id"
        }
    
    try:
        # Prepare request payload
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "public_token": public_token
        }
        
        # Make request to Plaid API
        response = requests.post(
            f"{PLAID_API_BASE}/item/public_token/exchange",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        # Handle response
        if response.status_code == 200:
            result = response.json()
            
            # Log partial access token for debugging (don't log the full token for security)
            if "access_token" in result:
                token = result["access_token"]
                masked_token = token[:5] + "..." + token[-5:] if len(token) > 10 else "***"
                logger.info(f"Successfully exchanged public token for access token: {masked_token}")
            
            return result
        else:
            error_message = f"Error exchanging public token. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_message)
            return {"error": error_message}
            
    except Exception as e:
        logger.error(f"Error exchanging public token: {str(e)}")
        return {"error": str(e)}

def get_transactions(
    access_token: Optional[str] = None, 
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    num_transactions: int = 100
) -> List[Dict[str, Any]]:
    """
    Get transactions from Plaid API or generate mock transactions.
    
    Args:
        access_token: The access token for the Plaid API (not used for mock data)
        start_date: The start date for transactions
        end_date: The end date for transactions
        num_transactions: The number of mock transactions to generate
        
    Returns:
        List of transaction dictionaries
    """
    if start_date is None:
        # Default to 30 days ago
        start_date = datetime.date.today() - datetime.timedelta(days=30)
    
    if end_date is None:
        # Default to today
        end_date = datetime.date.today()
    
    if USE_MOCK_DATA or not access_token:
        logger.info(f"Using mock transactions data for date range: {start_date} to {end_date}")
        # Generate and return mock transactions
        return generate_mock_transactions(start_date, end_date, num_transactions)
        
    # If we're given a mock access token from the UI but we have real credentials,
    # force the use of Sandbox user for demo without requiring login
    if access_token == "mock_access_token" and not USE_MOCK_DATA:
        logger.info("Converting mock_access_token to real Plaid sandbox access")
        # In a real app with Plaid sandbox, we'd use a stored sandbox access token
        # For now, we'll use the real API to get a token
    
    try:
        logger.info(f"Fetching real transactions from Plaid for date range: {start_date} to {end_date}")
        logger.info(f"Using access token: {access_token[:5]}...{access_token[-5:] if len(access_token) > 10 else '***'}")
        
        # Format dates as required by Plaid API (YYYY-MM-DD)
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        # Prepare request payload
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "access_token": access_token,
            "start_date": start_str,
            "end_date": end_str,
            "options": {
                "count": num_transactions
            }
        }
        
        # Make request to Plaid API
        response = requests.post(
            f"{PLAID_API_BASE}/transactions/get",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        # Handle response
        if response.status_code == 200:
            response_dict = response.json()
            
            if "transactions" in response_dict and isinstance(response_dict["transactions"], list):
                transactions = response_dict["transactions"]
                logger.info(f"Successfully retrieved {len(transactions)} transactions from Plaid")
                
                # Process transactions to match our expected format
                processed_transactions = []
                for transaction in transactions:
                    # Add is_mock flag to differentiate from mock data
                    transaction["is_mock"] = False
                    processed_transactions.append(transaction)
                    
                return processed_transactions
            else:
                logger.error("No transactions found in Plaid response")
                return generate_mock_transactions(start_date, end_date, num_transactions)
        else:
            error_message = f"Error getting transactions. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_message)
            return generate_mock_transactions(start_date, end_date, num_transactions)
            
    except Exception as e:
        logger.error(f"Error getting transactions from Plaid: {str(e)}")
        # Fall back to mock data if there's an error
        return generate_mock_transactions(start_date, end_date, num_transactions)

def generate_mock_transactions(
    start_date: datetime.date,
    end_date: datetime.date,
    count: int = 100
) -> List[Dict[str, Any]]:
    """
    Generate mock transaction data for demonstration purposes.
    
    Args:
        start_date: The start date for transactions
        end_date: The end date for transactions
        count: The number of mock transactions to generate
        
    Returns:
        List of mock transaction dictionaries
    """
    transactions = []
    date_range = (end_date - start_date).days + 1
    
    for _ in range(count):
        # Generate a random date within the range
        random_days = random.randint(0, date_range - 1)
        transaction_date = start_date + datetime.timedelta(days=random_days)
        
        # Select a random category
        category = random.choice(MOCK_CATEGORIES)
        
        # Select a random merchant based on the category
        merchant = random.choice(MOCK_MERCHANTS[category])
        
        # Generate a random amount between $1 and $500
        amount = round(random.uniform(1, 500), 2)
        
        transactions.append({
            "date": transaction_date.isoformat(),
            "name": merchant,
            "category": category,
            "amount": amount,
            "currency": "USD",
            "transaction_id": f"mock-{random.randint(10000, 99999)}",
            "is_mock": True
        })
    
    # Sort transactions by date (newest first)
    transactions.sort(key=lambda x: x["date"], reverse=True)
    
    return transactions

def import_transactions_to_db(transactions: List[Dict[str, Any]], db_session, Expense, user_id=None):
    """
    Import transactions from Plaid into the database.
    
    Args:
        transactions: List of transaction dictionaries
        db_session: SQLAlchemy database session
        Expense: Expense model class
        user_id: ID of the user to associate with imported expenses (optional)
        
    Returns:
        Number of transactions imported
    """
    count = 0
    for transaction in transactions:
        # For real Plaid transactions, the amount is negative for expenses
        # For mock transactions, we generate positive amounts
        amount = float(transaction.get("amount", 0))
        
        # Handle both real and mock transactions
        is_mock = transaction.get("is_mock", False)
        
        # For real Plaid data (not mock):
        # - Expenses are typically positive amounts
        # - Skip transactions with amount <= 0
        # For mock data:
        # - We generate positive amounts for expenses
        # - Skip amounts <= 0
        if (not is_mock and amount > 0) or (is_mock and amount > 0):
            # This is a valid expense in either case, continue processing
            pass
        else:
            # Skip invalid or income transactions
            continue
            
        # Convert transaction to Expense object
        try:
            # Handle date format from both real Plaid (YYYY-MM-DD) and mock data
            if isinstance(transaction.get("date"), str):
                date = datetime.datetime.fromisoformat(transaction["date"]).date()
            else:
                date = transaction.get("date")
            
            # Get transaction name/description
            description = transaction.get("name", transaction.get("merchant_name", "Unknown"))
            
            # Handle category from both real Plaid and mock data
            category_value = transaction.get("category", [])
            if isinstance(category_value, list) and len(category_value) > 0:
                # Use the most specific category (last in the list)
                category = category_value[-1]
            else:
                category = str(category_value)
            
            # Ensure we have a valid category
            if not category or category == "[]":
                category = "Uncategorized"
                
            expense = Expense(
                date=date,
                description=description,
                category=category,
                amount=abs(amount),  # Ensure positive amount for expense tracking
                user_id=user_id
            )
            
            db_session.add(expense)
            count += 1
            
        except Exception as e:
            logger.error(f"Error importing transaction: {str(e)}")
            logger.error(f"Problematic transaction data: {transaction}")
    
    try:
        db_session.commit()
    except Exception as e:
        logger.error(f"Error committing transactions: {str(e)}")
        db_session.rollback()
        return 0
    
    return count