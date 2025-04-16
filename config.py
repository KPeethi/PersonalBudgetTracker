"""
Configuration settings for the Expense Tracker application.
"""
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL not found, using SQLite instead")
    DATABASE_URL = "sqlite:///expense_tracker.db"

# Flask configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "myRandomSecretKey123!")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "myRandomSecretKey123!")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# Plaid configuration
PLAID_CLIENT_ID = os.environ.get("PLAID_CLIENT_ID")
PLAID_SECRET = os.environ.get("PLAID_SECRET")
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox")
PLAID_REDIRECT_URI = os.environ.get("PLAID_REDIRECT_URI", "http://localhost:5000/plaid/oauth-callback")

# OpenAI configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Check if we're in production environment
IS_PRODUCTION = ENVIRONMENT == "production"

# Print configuration for debugging
logger.info(f"Loaded environment variables from .env file")
logger.info(f"Using database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
logger.info(f"Starting application in {ENVIRONMENT} mode")
logger.info(f"Debug mode: {DEBUG}")