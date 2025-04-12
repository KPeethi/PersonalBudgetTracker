"""
OpenAI Service for Expense Tracker application.
Provides intelligent financial assistance using OpenAI's models.
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

# API Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = None

# Initialize client if API key is available
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized")
else:
    logger.warning("OpenAI API key not found in environment variables")


def check_api_availability() -> bool:
    """
    Check if the OpenAI API is properly configured and available.
    
    Returns:
        bool: True if the API is available, False otherwise
    """
    if not OPENAI_API_KEY or not openai_client:
        logger.warning("OpenAI API key not found in environment variables")
        print("ERROR: OPENAI_API_KEY is not set in environment variables")
        return False
    
    print(f"OpenAI API key is configured")
    logger.info(f"OpenAI API key is configured")
    
    # Make a simple test call to the API to check connectivity
    try:
        print("Making test request to OpenAI API...")
        # Test with a simple completion to check if API is working
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You respond with only 'OK' for testing purposes."},
                {"role": "user", "content": "Respond with OK to test API connectivity."}
            ],
            max_tokens=10
        )
        
        if response:
            logger.info("OpenAI API test successful")
            print("OpenAI API test successful - API is properly configured and responding")
            return True
        else:
            logger.error("OpenAI API test failed: No response")
            print("OpenAI API test failed: No response")
            return False
    except Exception as e:
        logger.exception(f"Error testing OpenAI API: {str(e)}")
        print(f"Error testing OpenAI API: {str(e)}")
        return False


def generate_response(
    query: str, 
    financial_context: Optional[str] = None,
    humor_level: str = "medium"
) -> Dict[str, Any]:
    """
    Generate a helpful response to a financial question using OpenAI.
    
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
            "error": "OpenAI API not configured",
            "response": "Sorry, I'm currently unavailable. Please check the API configuration."
        }
    
    # Create the system prompt for the professional financial assistant
    humor_instructions = {
        "low": "Be professional with minimal humor. Focus primarily on being helpful and informative.",
        "medium": "Be casual and friendly, use a conversational tone, and explain things simply while being helpful.",
        "high": "Be very casual and fun, use emojis occasionally, and keep things light while still being helpful."
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

{humor_instructions.get(humor_level, humor_instructions["medium"])}

Provide concise, accurate, and helpful answers about finances, budgeting, and expenses.
When giving financial advice, be responsible and avoid overly specific investment recommendations.
"""

    if financial_context:
        system_prompt += f"\nHere is some context about the user's finances: {financial_context}"

    try:
        print(f"Starting OpenAI API request for query: {query[:30]}...")
        logger.info(f"OpenAI API request initiated")
        
        # Make the API request
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=500
            )
            print(f"Received response from OpenAI")
        except Exception as e:
            print(f"Error making OpenAI request: {str(e)}")
            logger.error(f"OpenAI request error: {str(e)}")
            raise Exception(f"Error connecting to OpenAI: {str(e)}")
        
        # Parse and return the response
        if response and response.choices and len(response.choices) > 0:
            result = response.choices[0].message.content
            return {
                "success": True,
                "response": result
            }
        else:
            error_msg = "OpenAI API returned an empty response"
            print(error_msg)
            logger.error(error_msg)
            return {
                "success": False,
                "error": "API returned empty response",
                "response": "Sorry, I received an empty response. Please try again later."
            }
            
    except Exception as e:
        error_message = f"Error generating OpenAI response: {str(e)}"
        print(error_message)
        logger.exception(error_message)
        return {
            "success": False,
            "error": str(e),
            "response": f"Sorry, there was a technical issue. Please try again later. If the problem persists, contact support."
        }


def get_financial_tip(category: Optional[str] = None) -> str:
    """
    Get a financial tip related to a specific spending category.
    
    Args:
        category: Optional spending category to get a tip about
        
    Returns:
        String containing a financial tip
    """
    if not category:
        # General financial tip if no category is specified
        query = "Give a short, professional, and helpful financial tip in 1-2 sentences. Focus on practical advice."
    else:
        # Category-specific tip
        query = f"Give a short, professional, and helpful financial tip about {category} spending in 1-2 sentences. Focus on practical advice."
    
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
    Analyze a user's spending pattern and provide insights and recommendations.
    
    Args:
        expenses: List of expense objects or dictionaries
        
    Returns:
        String containing the AI analysis
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
    
    query = "Based on this spending data, provide a professional and insightful analysis. Include one practical tip. Use a friendly professional tone."
    
    result = generate_response(query, financial_context=expense_context, humor_level="low")
    if result["success"]:
        return result["response"]
    else:
        return "I couldn't analyze your spending patterns right now. Please try again later."