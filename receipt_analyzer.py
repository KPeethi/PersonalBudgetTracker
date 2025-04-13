"""
Receipt Analyzer module for the Expense Tracker application.
Extracts information from receipt images using OpenAI's GPT-4 Vision API.
"""
import os
import base64
import logging
import re
from openai import OpenAI

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def encode_image_to_base64(image_path):
    """
    Encode an image file to base64.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image: {str(e)}")
        return None

def extract_total_amount(image_path):
    """
    Extract the total amount from a receipt image.
    
    Args:
        image_path: Path to the receipt image
        
    Returns:
        Float representing the total amount, or None if extraction failed
    """
    try:
        # Encode the image
        base64_image = encode_image_to_base64(image_path)
        if not base64_image:
            return None
        
        # System prompt for the analysis
        system_prompt = """
        You are a smart OCR and receipt analysis AI. Your job is to extract the total amount spent 
        from scanned receipts. Always return only the final amount paid in U.S. dollars. 
        If there is a breakdown (items, taxes, tips), still give the grand total.
        Ignore anything that looks like change or balance. If the image is not a valid receipt, 
        return: "No valid receipt found."
        ONLY return the dollar amount as a number (e.g., 42.99) without any additional text or explanation.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the total amount from this receipt."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            max_tokens=100
        )
        
        # Get the response text
        result = response.choices[0].message.content.strip()
        
        # Check if it's a valid receipt
        if result == "No valid receipt found.":
            return None
        
        # Try to extract just the number from the response
        amount_match = re.search(r'(\d+\.\d{2})', result)
        if amount_match:
            return float(amount_match.group(1))
        
        # If it's just a number, convert it
        try:
            return float(result)
        except ValueError:
            # If neither pattern works, log the error and return None
            logger.error(f"Could not parse amount from OpenAI response: {result}")
            return None
            
    except Exception as e:
        logger.error(f"Error in receipt analysis: {str(e)}")
        return None

def get_receipt_details(image_path):
    """
    Get comprehensive details from a receipt image.
    
    Args:
        image_path: Path to the receipt image
        
    Returns:
        Dictionary with receipt details or None if extraction failed
    """
    try:
        # Encode the image
        base64_image = encode_image_to_base64(image_path)
        if not base64_image:
            return None
        
        # System prompt for the comprehensive analysis
        system_prompt = """
        You are an expert receipt analysis AI. Extract the following information from the receipt:
        1. Total amount
        2. Date of purchase
        3. Merchant/store name
        4. Items purchased (if visible)
        5. Category of purchase (e.g., Groceries, Restaurant, etc.)
        
        Format your response as JSON with the following structure:
        {
            "total": float,
            "date": "YYYY-MM-DD",
            "merchant": "string",
            "items": ["item1", "item2", ...],
            "category": "string"
        }
        
        If the image is not a valid receipt, or if any field cannot be determined, use null for that field.
        """
        
        # Call OpenAI API with JSON response format
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this receipt and extract the requested details."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=500
        )
        
        # Parse the JSON response
        import json
        result = json.loads(response.choices[0].message.content)
        return result
            
    except Exception as e:
        logger.error(f"Error in detailed receipt analysis: {str(e)}")
        return None