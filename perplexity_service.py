"""
Perplexity AI Service for Expense Tracker application.
Provides intelligent and witty financial assistance using Perplexity's AI models.
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# API Configuration
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def check_api_availability() -> bool:
    """
    Check if the Perplexity API is properly configured and available.
    
    Returns:
        bool: True if the API is available, False otherwise
    """
    if not PERPLEXITY_API_KEY:
        logger.warning("Perplexity API key not found in environment variables")
        print("ERROR: PERPLEXITY_API_KEY is not set in environment variables")
        return False
    
    print(f"Perplexity API key is configured (length: {len(PERPLEXITY_API_KEY)})")
    logger.info(f"Perplexity API key is configured (length: {len(PERPLEXITY_API_KEY)})")
    
    # Check if API key has a valid format (length, characters)
    if len(PERPLEXITY_API_KEY.strip()) < 30:  # Perplexity API keys are typically longer
        logger.warning(f"Perplexity API key appears to be too short: length={len(PERPLEXITY_API_KEY.strip())}")
        print(f"WARNING: PERPLEXITY_API_KEY appears too short (length={len(PERPLEXITY_API_KEY.strip())})")
    
    # Make a simple test call to the API to check connectivity
    try:
        print("Making test request to Perplexity API...")
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        simple_payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "You respond with only 'OK' for testing purposes."},
                {"role": "user", "content": "Respond with OK to test API connectivity."}
            ],
            "max_tokens": 10,
            "temperature": 0.0,
            "stream": False
        }
        
        # Make a simple test request
        response = requests.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=simple_payload,
            timeout=5  # Short timeout for testing
        )
        
        print(f"API test response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Perplexity API test successful")
            print("Perplexity API test successful - API is properly configured and responding")
            return True
        else:
            logger.error(f"Perplexity API test failed: {response.status_code}, {response.text[:200]}")
            print(f"Perplexity API test failed with status code {response.status_code}")
            print(f"Error response: {response.text[:200]}...")
            return False
    except Exception as e:
        logger.exception(f"Error testing Perplexity API: {str(e)}")
        print(f"Error testing Perplexity API: {str(e)}")
        return False


def generate_response(
    query: str, 
    financial_context: Optional[str] = None,
    humor_level: str = "medium"
) -> Dict[str, Any]:
    """
    Generate a witty and helpful response to a financial question using Perplexity API.
    
    Args:
        query: The user's question or message
        financial_context: Optional context about the user's finances to make responses more relevant
        humor_level: Level of humor to include in responses ("low", "medium", "high")
        
    Returns:
        Dictionary containing the response and metadata
    """
    if not check_api_availability():
        return {
            "success": False,
            "error": "Perplexity API not configured",
            "response": "Sorry, I'm currently unavailable. Please check the API configuration."
        }
    
    # Create the system prompt for the professional financial assistant
    humor_instructions = {
        "low": "Be lightly humorous occasionally, but focus primarily on being helpful.",
        "medium": "Be casual and friendly, use emojis occasionally, and explain things simply while being helpful.",
        "high": "Be very casual and fun, use emojis freely, and drop Gen Z-style lingo while still being helpful."
    }
    
    system_prompt = f"""You are a professional, friendly financial assistant embedded in an expense tracking application. 
Your job is to help users understand their spending, income, and financial patterns.

Your goals:
- Be polite, concise, and supportive in all responses
- Answer questions about expenses, income, and categories accurately
- Offer practical suggestions on saving, budgeting, and spending improvements
- Help users understand trends and data summaries
- Provide step-by-step guidance when needed
- Keep responses clear and non-technical when possible

Do NOT make jokes. Use short paragraphs or bullet points for clarity when explaining complex information.
Keep your tone friendly but professional.

Provide concise, accurate, and helpful answers about finances, budgeting, and expenses.
When giving financial advice, be responsible and avoid overly specific investment recommendations.
"""

    if financial_context:
        system_prompt += f"\nHere is some context about the user's finances: {financial_context}"

    try:
        print(f"DEBUG - Starting Perplexity API request for query: {query[:30]}...")
        logger.info(f"DEBUG - Perplexity API request initiated. API Key exists: {bool(PERPLEXITY_API_KEY)}")
        
        # Prepare the request headers and payload
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print(f"DEBUG - Headers prepared (without showing actual key)")
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.7,
            # Use max_tokens as a number, not a string
            "max_tokens": 300,
            "top_p": 0.9,
            # Using standard parameters supported by Perplexity API
            "presence_penalty": 0.0,  # Instead of frequency_penalty
            "frequency_penalty": 0.0,
            "stream": False  # Ensure we're not trying to stream
        }
        
        print(f"DEBUG - Payload prepared, system prompt length: {len(system_prompt)}, query length: {len(query)}")
        
        # Log the request for debugging purposes
        logger.debug(f"Perplexity API request: {payload}")
        
        # Make the API request
        print(f"DEBUG - Making request to API endpoint: {PERPLEXITY_API_URL}")
        print(f"DEBUG - Request timeout set to default")
        
        try:
            response = requests.post(
                PERPLEXITY_API_URL,
                headers=headers,
                json=payload,
                timeout=25  # Set a 25-second timeout
            )
            print(f"DEBUG - Received response with status code: {response.status_code}")
            
            # Log the response for debugging
            logger.debug(f"Perplexity API response code: {response.status_code}")
            
            # Log response headers for debugging
            logger.debug(f"Response headers: {dict(response.headers)}")
            print(f"DEBUG - Response headers received: Content-Type={response.headers.get('Content-Type')}")
        except requests.exceptions.Timeout:
            print("DEBUG - Request timed out after 25 seconds")
            logger.error("Perplexity API request timed out after 25 seconds")
            raise Exception("Request timed out. The server took too long to respond.")
        
        # Parse and return the response
        if response.status_code == 200:
            result = response.json()
            logger.debug(f"Successful response received: {result}")
            
            try:
                # Check if the expected fields are present
                if "choices" not in result or not result["choices"]:
                    error_msg = "Perplexity API returned empty choices"
                    print(error_msg)
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": "API returned invalid response format",
                        "response": "Sorry, I received an unexpected response format from the API. Please try again later."
                    }
                
                # Check if message content is available
                if "message" not in result["choices"][0] or "content" not in result["choices"][0]["message"]:
                    error_msg = "Perplexity API response missing message content"
                    print(error_msg)
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": "API response missing content",
                        "response": "Sorry, the API response is missing the expected content. Please try again later."
                    }
                
                return {
                    "success": True,
                    "response": result["choices"][0]["message"]["content"],
                    "citations": result.get("citations", []),
                    "usage": result.get("usage", {})
                }
            except Exception as e:
                error_msg = f"Error parsing successful API response: {str(e)}"
                print(error_msg)
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": f"Response parsing error: {str(e)}",
                    "response": "Sorry, I had trouble processing the API response. Please try again later."
                }
        elif response.status_code == 400:
            # Bad request - likely an issue with our parameters
            error_text = f"Bad request to Perplexity API: {response.text}"
            print(error_text)
            logger.error(error_text)
            
            # Try to parse the error response
            try:
                error_details = response.json()
                error_message = error_details.get("error", {}).get("message", "Unknown error")
                print(f"API error details: {error_message}")
                
                return {
                    "success": False,
                    "error": f"API Error (400): {error_message}",
                    "response": "I encountered a technical issue with the API request format. Our team has been notified."
                }
            except:
                return {
                    "success": False,
                    "error": f"API Error (400): Could not parse error details",
                    "response": "I encountered a technical issue with the API request. Our team has been notified."
                }
        elif response.status_code == 401:
            # Authentication error
            error_msg = "Perplexity API authentication error: Invalid API key"
            print(error_msg)
            logger.error(error_msg)
            return {
                "success": False,
                "error": "API authentication failed",
                "response": "I'm currently experiencing authentication issues with my AI service. Our team has been notified about this issue."
            }
        elif response.status_code == 429:
            # Rate limit error
            error_msg = "Perplexity API rate limit exceeded"
            print(error_msg)
            logger.error(error_msg)
            return {
                "success": False,
                "error": "API rate limit exceeded",
                "response": "I've reached my usage limit with the AI service. Please try again later."
            }
        elif response.status_code >= 500:
            # Server error
            error_msg = f"Perplexity API server error: {response.status_code}"
            print(error_msg)
            logger.error(error_msg)
            return {
                "success": False,
                "error": f"API server error: {response.status_code}",
                "response": "The AI service is currently experiencing technical difficulties. Please try again later."
            }
        else:
            # Other errors
            error_msg = f"Perplexity API error: {response.status_code}, {response.text}"
            print(error_msg)
            logger.error(error_msg)
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "response": f"Sorry, I encountered an issue with the Perplexity API. Please try again later."
            }
            
    except Exception as e:
        error_message = f"Error generating Perplexity response: {str(e)}"
        print(error_message)
        logger.exception(error_message)
        return {
            "success": False,
            "error": str(e),
            "response": f"Sorry, there was a technical issue: {str(e)}. Please try again later. If the problem persists, contact support."
        }


def get_financial_tip(category: Optional[str] = None) -> str:
    """
    Get a witty financial tip related to a specific spending category.
    
    Args:
        category: Optional spending category to get a tip about
        
    Returns:
        String containing a financial tip with humor
    """
    if not category:
        # General financial tip if no category is specified
        query = "Give a short, professional, and helpful financial tip in 1-2 sentences. Focus on practical advice without humor."
    else:
        # Category-specific tip
        query = f"Give a short, professional, and helpful financial tip about {category} spending in 1-2 sentences. Focus on practical advice without humor."
    
    result = generate_response(query, humor_level="low")
    if result["success"]:
        return result["response"]
    else:
        # Fallback tips if API fails - professional tone
        fallback_tips = [
            "Consider automating your savings by setting up regular transfers on payday to ensure consistent contributions toward your financial goals.",
            "Track all expenses, even small ones, as they can add up quickly and impact your overall budget significantly over time.",
            "Review your subscription services quarterly to identify and cancel those you no longer use or need.",
            "When making major purchases, implement a 24-hour waiting period to avoid impulse buying and ensure the expense aligns with your priorities."
        ]
        import random
        return random.choice(fallback_tips)


def analyze_spending_pattern(expenses: List[Dict[str, Any]]) -> str:
    """
    Analyze a user's spending pattern and provide witty insights and recommendations.
    
    Args:
        expenses: List of expense objects or dictionaries
        
    Returns:
        String containing the AI analysis with humor
    """
    # Format the expenses data for the API
    total_spent = sum(expense.get("amount", 0) for expense in expenses)
    categories = {}
    for expense in expenses:
        category = expense.get("category", "Uncategorized")
        if category in categories:
            categories[category] += expense.get("amount", 0)
        else:
            categories[category] = expense.get("amount", 0)
    
    # Sort categories by amount spent
    sorted_categories = sorted(
        categories.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    top_categories = sorted_categories[:3]
    
    # Create context for analysis
    expense_context = f"""
    Total spent: ${total_spent:.2f}
    Top spending categories:
    {', '.join([f'{cat}: ${amt:.2f}' for cat, amt in top_categories])}
    Number of expenses: {len(expenses)}
    """
    
    query = "Based on this spending data, provide a professional and insightful analysis. Include one practical tip. Use a friendly but professional tone without humor."
    
    result = generate_response(query, financial_context=expense_context, humor_level="low")
    if result["success"]:
        return result["response"]
    else:
        return "I couldn't analyze your spending patterns right now. Please try again later."