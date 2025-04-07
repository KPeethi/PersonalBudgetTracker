"""
Configuration settings for the Expense Tracker application.
Update these settings to match your environment.
"""

import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment Detection
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = not IS_PRODUCTION

# Database Configuration
# The application supports both PostgreSQL and MySQL

# PostgreSQL is used by default on Replit
DATABASE_URL = os.environ.get("DATABASE_URL")

# For local MySQL deployments, uncomment and configure this:
# DATABASE_URL = "mysql+pymysql://username:password@localhost/ExpenseDB"

if not DATABASE_URL:
    logger.warning("No DATABASE_URL found in environment, using SQLite as fallback")
    DATABASE_URL = "sqlite:///expense_tracker.db"
else:
    logger.info(f"Using database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

# Plaid API Configuration
PLAID_CLIENT_ID = os.environ.get("PLAID_CLIENT_ID", "67a4290da237bf001e5c7ac6")
PLAID_SECRET = os.environ.get("PLAID_SECRET", "02e5286ff3222322801b1649e99ca5")
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox")

# Plaid Redirect URI - Update with your domain
current_domain = os.environ.get("REPL_SLUG", "localhost:5000")
if "localhost" in current_domain:
    protocol = "http"
else:
    protocol = "https"
    
PLAID_REDIRECT_URI = os.environ.get(
    "PLAID_REDIRECT_URI", 
    f"{protocol}://{current_domain}/plaid/oauth-callback"
)

# Flask Application Settings
SECRET_KEY = os.environ.get("SECRET_KEY", "development-key-change-in-production")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "t")

# OpenAI API Configuration for AI Assistant
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024

# Security Configuration
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_SECURE = IS_PRODUCTION
REMEMBER_COOKIE_HTTPONLY = True

# Print configuration summary
logger.info(f"Starting application in {ENVIRONMENT} mode")
logger.info(f"Debug mode: {DEBUG}")
logger.info(f"Using Plaid environment: {PLAID_ENV}")
logger.info(f"Plaid redirect URI: {PLAID_REDIRECT_URI}")
logger.info(f"OpenAI API configured: {'Yes' if OPENAI_API_KEY else 'No'}")