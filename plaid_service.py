"""
Plaid integration module for the Expense Tracker application.
Used to fetch financial data from Plaid for demonstration purposes.
"""

import os
import datetime
import random
import logging
from typing import List, Dict, Any, Optional

import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

# Configure logging
logger = logging.getLogger(__name__)

# Check if Plaid credentials are available
PLAID_CLIENT_ID = os.environ.get('PLAID_CLIENT_ID')
PLAID_SECRET = os.environ.get('PLAID_SECRET')

# Flag to determine if we use real Plaid or mock data
USE_MOCK_DATA = not (PLAID_CLIENT_ID and PLAID_SECRET)

# Initialize Plaid client if credentials are available
plaid_client = None
if not USE_MOCK_DATA:
    try:
        configuration = plaid.Configuration(
            host=plaid.Environment.Sandbox,
            api_key={
                'clientId': PLAID_CLIENT_ID,
                'secret': PLAID_SECRET,
            }
        )
        api_client = plaid.ApiClient(configuration)
        plaid_client = plaid_api.PlaidApi(api_client)
        logger.info("Plaid client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Plaid client: {str(e)}")
        USE_MOCK_DATA = True

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
        return {
            "link_token": "mock_link_token",
            "expiration": datetime.datetime.now().isoformat(),
            "request_id": "mock_request_id"
        }
    
    try:
        # Create a link token with configs
        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="Expense Tracker",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(random.randint(10000, 99999))
            )
        )
        response = plaid_client.link_token_create(request)
        return response.to_dict()
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
        # Exchange the public token for an access token
        request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        response = plaid_client.item_public_token_exchange(request)
        return response.to_dict()
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
        # Generate and return mock transactions
        return generate_mock_transactions(start_date, end_date, num_transactions)
    
    try:
        # Get transactions from Plaid API
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                count=num_transactions
            )
        )
        response = plaid_client.transactions_get(request)
        return response.to_dict()["transactions"]
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
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

def import_transactions_to_db(transactions: List[Dict[str, Any]], db_session, Expense):
    """
    Import transactions from Plaid into the database.
    
    Args:
        transactions: List of transaction dictionaries
        db_session: SQLAlchemy database session
        Expense: Expense model class
        
    Returns:
        Number of transactions imported
    """
    count = 0
    for transaction in transactions:
        # Skip positive amounts (income) - we're just tracking expenses
        if float(transaction["amount"]) <= 0:
            continue
            
        # Convert transaction to Expense object
        try:
            date = datetime.datetime.fromisoformat(transaction["date"]).date()
            expense = Expense(
                date=date,
                description=transaction["name"],
                category=transaction["category"][0] if isinstance(transaction["category"], list) else transaction["category"],
                amount=abs(float(transaction["amount"]))  # Ensure positive amount
            )
            
            db_session.add(expense)
            count += 1
        except Exception as e:
            logger.error(f"Error importing transaction: {str(e)}")
    
    try:
        db_session.commit()
    except Exception as e:
        logger.error(f"Error committing transactions: {str(e)}")
        db_session.rollback()
        return 0
    
    return count