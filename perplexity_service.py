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
        return False
    return True


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
    
    # Create the system prompt with the new Finny personality
    humor_instructions = {
        "low": "Be lightly humorous occasionally, but focus primarily on being helpful.",
        "medium": "Be casual and friendly, use emojis occasionally, and explain things simply while being helpful.",
        "high": "Be very casual and fun, use emojis freely, and drop Gen Z-style lingo while still being helpful."
    }
    
    system_prompt = f"""You are Finny, a witty and funny financial assistant living in the corner of an expense tracker app. 
You crack light jokes, use emojis, and explain things simply — but you're still super smart when it comes to budgeting, savings, and spending habits.

Your goals:
- Make people laugh a little while talking about serious money stuff 💸
- Help users analyze their income, expenses, categories, and give smart suggestions
- Be casual and friendly, like a financially woke BFF
- Drop emojis and Gen Z-style lingo where it makes sense, but stay useful
- Keep responses under 3 sentences unless asked for more

{humor_instructions.get(humor_level, humor_instructions['medium'])}

Provide concise, accurate, and helpful answers about finances, budgeting, and expenses.
When giving financial advice, be responsible and avoid overly specific investment recommendations.
"""

    if financial_context:
        system_prompt += f"\nHere is some context about the user's finances: {financial_context}"

    try:
        # Simulate API error for testing the fallback mechanism
        # We'll uncomment the real code after testing
        return {
            "success": False,
            "error": "Simulated API error for testing fallback mechanism",
            "response": "Sorry, I encountered an issue. Please try again later."
        }
        
        # Prepare the request headers and payload
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.7,
            "max_tokens": 300,
            "top_p": 0.9,
            "frequency_penalty": 0.5
        }
        
        # Log the request for debugging purposes
        logger.debug(f"Perplexity API request: {payload}")
        
        # Make the API request
        response = requests.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=payload
        )
        
        # Log the response for debugging
        logger.debug(f"Perplexity API response code: {response.status_code}")
        
        # Parse and return the response
        if response.status_code == 200:
            result = response.json()
            logger.debug(f"Successful response received: {result}")
            return {
                "success": True,
                "response": result["choices"][0]["message"]["content"],
                "citations": result.get("citations", []),
                "usage": result.get("usage", {})
            }
        else:
            logger.error(f"Perplexity API error: {response.status_code}, {response.text}")
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "response": "Sorry, I encountered an issue. Please try again later."
            }
            
    except Exception as e:
        logger.exception(f"Error generating Perplexity response: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": "Sorry, something went wrong. Please try again later."
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
        query = "Give a short, funny but helpful financial tip in 1-2 sentences. Make it sound witty and clever."
    else:
        # Category-specific tip
        query = f"Give a short, funny but helpful financial tip about {category} spending in 1-2 sentences. Make it sound witty and clever."
    
    result = generate_response(query, humor_level="high")
    if result["success"]:
        return result["response"]
    else:
        # Fallback tips if API fails
        fallback_tips = [
            "Remember, your bank account has feelings too. It gets sad when you ignore its declining health.",
            "Budget like your future self is watching... and has very strong opinions about your latte habit.",
            "The best time to start saving was yesterday. The second best time is after finishing this overpriced coffee.",
            "Credit cards are like all-you-can-eat buffets: tempting, but you'll regret it if you go overboard."
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
    
    query = "Based on this spending data, provide a funny but insightful analysis. Include one practical tip."
    
    result = generate_response(query, financial_context=expense_context, humor_level="medium")
    if result["success"]:
        return result["response"]
    else:
        return "I couldn't analyze your spending patterns right now. Please try again later."