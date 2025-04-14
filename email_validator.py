"""
Email validation module for the Expense Tracker application.
Provides advanced email validation functionality beyond basic format checks.
"""
import re
import logging

# Set up logger
logger = logging.getLogger(__name__)

def is_valid_gmail_address(email):
    """
    Check if an email address is a valid Gmail address that appears to be created by a real person.
    
    Args:
        email: The email address to validate
        
    Returns:
        tuple: (is_valid, message) where is_valid is a boolean and message contains validation details
    """
    # Make sure it's a Gmail address
    if not email.lower().endswith('@gmail.com'):
        return True, None  # Not a Gmail address, so we don't apply special validation
    
    # Extract the username part (before @gmail.com)
    username = email.split('@')[0].lower()
    
    # Check minimum length
    if len(username) < 6:
        return False, "Gmail addresses are typically at least 6 characters before the @ symbol."
    
    # Check for patterns that suggest test or fake emails
    test_patterns = [
        r'^test',  # Starts with 'test'
        r'test$',  # Ends with 'test'
        r'^[a-z]{1,3}\d{3,}',  # Short letter prefix followed by 3+ digits (abc123)
        r'^admin',  # Starts with 'admin'
        r'^user\d+',  # Patterns like user123
        r'^temp',  # Starts with 'temp'
        r'^fake',  # Starts with 'fake'
        r'^\d{3,}',  # Starts with 3+ digits
        r'^[a-z]+\d{4,}',  # Letter(s) followed by 4+ digits
        r'^sample',  # Starts with 'sample'
        r'^demo',  # Starts with 'demo'
        r'^dummy',  # Starts with 'dummy'
    ]
    
    # Check for repeated characters (aaaaa, 11111)
    if re.search(r'(.)\1{4,}', username):
        return False, "This email contains too many repeated characters, which is uncommon for real addresses."
    
    # Check for keyboard patterns (qwerty, 12345)
    keyboard_patterns = ['qwerty', 'asdfgh', '123456', 'zxcvbn']
    for pattern in keyboard_patterns:
        if pattern in username:
            return False, "This email contains keyboard patterns that suggest it may be a test account."
    
    # Check test patterns
    for pattern in test_patterns:
        if re.search(pattern, username):
            return False, "This email matches patterns commonly used for test or temporary accounts."
    
    # If it passed all checks, it's probably valid
    return True, None

def validate_registration_email(email):
    """
    Validate an email address for registration.
    This performs both standard format validation and additional checks for 
    Gmail addresses to identify potentially fake accounts.
    
    Args:
        email: The email address to validate
        
    Returns:
        tuple: (is_valid, message) where is_valid is a boolean and message contains validation details
    """
    # Basic format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format."
    
    # If it's a Gmail address, perform additional validation
    if email.lower().endswith('@gmail.com'):
        is_valid, message = is_valid_gmail_address(email)
        if not is_valid:
            return False, message
    
    return True, None