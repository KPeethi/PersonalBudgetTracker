"""
Conversational AI Assistant module for the Expense Tracker application.
Allows natural language queries about expenses and finances.
"""

import datetime
import os
import re
import logging
import json
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import text, func, extract
from models import Expense, User, db, CustomBudgetCategory
from flask_login import current_user
import config

# Set up logging
logger = logging.getLogger(__name__)

# Import OpenAI
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or config.OPENAI_API_KEY
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        OPENAI_MODEL = "gpt-4o" 
        logger.debug(f"OpenAI API configured with model: {OPENAI_MODEL}")
    else:
        openai_client = None
        logger.warning("OpenAI API key not configured")
        OPENAI_MODEL = "gpt-4o"  # Default model
except ImportError:
    openai_client = None
    logger.warning("OpenAI package not available")
    OPENAI_MODEL = "gpt-4o"  # Default model
except Exception as e:
    openai_client = None
    logger.error(f"Error initializing OpenAI: {str(e)}")
    OPENAI_MODEL = "gpt-4o"  # Default model

# Common query patterns and their SQL translations
QUERY_PATTERNS = {
    "category_total": {
        "pattern": r"(how much|total|spent|spend|sum) .* (on|in) (?P<category>\w+)",
        "sql_template": "SELECT SUM(amount) FROM expenses WHERE category ILIKE :category AND user_id = :user_id {time_filter}"
    },
    "timeframe_total": {
        "pattern": r"(how much|total|spent|spend|sum) .* (last|this) (?P<timeframe>week|month|year)",
        "sql_template": "SELECT SUM(amount) FROM expenses WHERE user_id = :user_id {time_filter}"
    },
    "category_in_timeframe": {
        "pattern": r"(how much|total|spent|spend|sum) .* (on|in) (?P<category>\w+) .* (last|this) (?P<timeframe>week|month|year)",
        "sql_template": "SELECT SUM(amount) FROM expenses WHERE category ILIKE :category AND user_id = :user_id {time_filter}"
    },
    "top_expenses": {
        "pattern": r"(top|highest|largest|biggest) (?P<count>\d+)? ?expenses",
        "sql_template": "SELECT * FROM expenses WHERE user_id = :user_id {time_filter} ORDER BY amount DESC LIMIT :limit"
    },
    "category_comparison": {
        "pattern": r"(compare|comparison|breakdown|distribution) .* (categories|spending)",
        "sql_template": "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = :user_id {time_filter} GROUP BY category ORDER BY total DESC"
    },
    "month_comparison": {
        "pattern": r"(compare|comparison|monthly|months) .* (spending|expenses)",
        "sql_template": "SELECT EXTRACT(YEAR FROM date) as year, EXTRACT(MONTH FROM date) as month, SUM(amount) as total FROM expenses WHERE user_id = :user_id GROUP BY year, month ORDER BY year, month"
    },
    "category_explosion": {
        "pattern": r"(which|what) category (exploded|increased|grew|rose) .* (this|last) (?P<timeframe>month|year)",
        "sql_template": """
            WITH current_period AS (
                SELECT category, SUM(amount) as current_total 
                FROM expenses 
                WHERE user_id = :user_id {current_time_filter}
                GROUP BY category
            ),
            previous_period AS (
                SELECT category, SUM(amount) as previous_total 
                FROM expenses 
                WHERE user_id = :user_id {previous_time_filter}
                GROUP BY category
            )
            SELECT c.category, c.current_total, p.previous_total, 
                   (c.current_total - COALESCE(p.previous_total, 0)) as difference,
                   CASE WHEN p.previous_total > 0 
                        THEN ((c.current_total - p.previous_total) / p.previous_total * 100)
                        ELSE NULL END as percentage_change
            FROM current_period c
            LEFT JOIN previous_period p ON c.category = p.category
            ORDER BY percentage_change DESC NULLS LAST
        """
    }
}

def get_time_filter(timeframe: str, ref_date: datetime.date = None) -> Tuple[str, Dict[str, Any]]:
    """Generate SQL time filter based on timeframe."""
    if not ref_date:
        ref_date = datetime.date.today()
    
    params = {}
    
    if timeframe == 'week':
        # Get the start of the current week (Monday)
        start_of_week = ref_date - datetime.timedelta(days=ref_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        filter_clause = "AND date BETWEEN :start_date AND :end_date"
        params['start_date'] = start_of_week
        params['end_date'] = end_of_week
    
    elif timeframe == 'month':
        # Current month
        start_of_month = datetime.date(ref_date.year, ref_date.month, 1)
        # Get the last day of current month
        if ref_date.month == 12:
            end_of_month = datetime.date(ref_date.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_of_month = datetime.date(ref_date.year, ref_date.month + 1, 1) - datetime.timedelta(days=1)
        
        filter_clause = "AND date BETWEEN :start_date AND :end_date"
        params['start_date'] = start_of_month
        params['end_date'] = end_of_month
    
    elif timeframe == 'year':
        # Current year
        start_of_year = datetime.date(ref_date.year, 1, 1)
        end_of_year = datetime.date(ref_date.year, 12, 31)
        
        filter_clause = "AND date BETWEEN :start_date AND :end_date"
        params['start_date'] = start_of_year
        params['end_date'] = end_of_year
    
    else:
        # No time filter
        filter_clause = ""
    
    return filter_clause, params

def get_previous_period_filter(timeframe: str, ref_date: datetime.date = None) -> Tuple[str, Dict[str, Any]]:
    """Generate SQL filter for previous time period based on timeframe."""
    if not ref_date:
        ref_date = datetime.date.today()
    
    params = {}
    
    if timeframe == 'week':
        # Previous week
        start_of_current_week = ref_date - datetime.timedelta(days=ref_date.weekday())
        start_of_prev_week = start_of_current_week - datetime.timedelta(days=7)
        end_of_prev_week = start_of_prev_week + datetime.timedelta(days=6)
        
        filter_clause = "AND date BETWEEN :prev_start_date AND :prev_end_date"
        params['prev_start_date'] = start_of_prev_week
        params['prev_end_date'] = end_of_prev_week
    
    elif timeframe == 'month':
        # Previous month
        if ref_date.month == 1:
            prev_month = 12
            prev_year = ref_date.year - 1
        else:
            prev_month = ref_date.month - 1
            prev_year = ref_date.year
            
        start_of_prev_month = datetime.date(prev_year, prev_month, 1)
        
        # Get the last day of previous month
        if prev_month == 12:
            end_of_prev_month = datetime.date(prev_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_of_prev_month = datetime.date(prev_year, prev_month + 1, 1) - datetime.timedelta(days=1)
        
        filter_clause = "AND date BETWEEN :prev_start_date AND :prev_end_date"
        params['prev_start_date'] = start_of_prev_month
        params['prev_end_date'] = end_of_prev_month
    
    elif timeframe == 'year':
        # Previous year
        prev_year = ref_date.year - 1
        start_of_prev_year = datetime.date(prev_year, 1, 1)
        end_of_prev_year = datetime.date(prev_year, 12, 31)
        
        filter_clause = "AND date BETWEEN :prev_start_date AND :prev_end_date"
        params['prev_start_date'] = start_of_prev_year
        params['prev_end_date'] = end_of_prev_year
    
    else:
        # No time filter
        filter_clause = ""
    
    return filter_clause, params

def analyze_query(query_text: str) -> Dict[str, Any]:
    """
    Analyze a natural language query and identify the appropriate SQL query pattern.
    
    Args:
        query_text: User's natural language query
        
    Returns:
        Dictionary with query information including pattern, params and SQL template
    """
    query_text = query_text.lower().strip()
    
    # Try to match against known patterns
    for query_type, pattern_info in QUERY_PATTERNS.items():
        match = re.search(pattern_info['pattern'], query_text)
        if match:
            logger.debug(f"Matched query type: {query_type}")
            
            result = {
                'query_type': query_type,
                'sql_template': pattern_info['sql_template'],
                'params': {'user_id': current_user.id if current_user else None}
            }
            
            # Extract parameters from the match
            for param_name, param_value in match.groupdict().items():
                result['params'][param_name] = param_value
            
            # Handle common parameters
            if 'category' in result['params']:
                # Add wildcards to make it a partial match
                result['params']['category'] = f"%{result['params']['category']}%"
            
            if 'count' in result['params'] and result['params']['count']:
                try:
                    result['params']['limit'] = int(result['params']['count'])
                except ValueError:
                    result['params']['limit'] = 5  # Default if count is not a valid number
            else:
                # Default limit for top expenses
                result['params']['limit'] = 5
            
            # Handle time filter
            if 'timeframe' in result['params']:
                timeframe = result['params']['timeframe']
                
                if query_type == 'category_explosion':
                    # For category explosion, we need both current and previous period filters
                    current_filter, current_params = get_time_filter(timeframe)
                    previous_filter, previous_params = get_previous_period_filter(timeframe)
                    
                    # Update SQL template with filters
                    result['sql_template'] = result['sql_template'].format(
                        current_time_filter=current_filter,
                        previous_time_filter=previous_filter
                    )
                    
                    # Add parameters
                    result['params'].update(current_params)
                    result['params'].update(previous_params)
                else:
                    # Regular time filter
                    time_filter, time_params = get_time_filter(timeframe)
                    
                    # Update SQL template with time filter
                    result['sql_template'] = result['sql_template'].format(time_filter=time_filter)
                    
                    # Add time parameters
                    result['params'].update(time_params)
            else:
                # No time filter specified
                if 'time_filter' in result['sql_template']:
                    result['sql_template'] = result['sql_template'].format(time_filter="")
                
                # For category explosion, use default of this month vs last month
                if query_type == 'category_explosion':
                    current_filter, current_params = get_time_filter('month')
                    previous_filter, previous_params = get_previous_period_filter('month')
                    
                    result['sql_template'] = result['sql_template'].format(
                        current_time_filter=current_filter,
                        previous_time_filter=previous_filter
                    )
                    
                    result['params'].update(current_params)
                    result['params'].update(previous_params)
            
            return result
    
    # If no pattern match, use AI to generate response
    return {
        'query_type': 'unmatched',
        'params': {'user_id': current_user.id if current_user else None}
    }

def execute_query(query_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the SQL query based on query info.
    
    Args:
        query_info: Dictionary with query parameters
        
    Returns:
        Dictionary with query results
    """
    if query_info['query_type'] == 'unmatched':
        # Unmatched query, will be handled by AI instead
        return {
            'type': 'unmatched',
            'data': None
        }
    
    try:
        sql = query_info['sql_template']
        params = query_info['params']
        
        # Execute the query
        if 'SELECT SUM' in sql:
            # Aggregate query
            result = db.session.execute(text(sql), params).scalar()
            return {
                'type': 'aggregate',
                'data': result or 0
            }
        elif 'GROUP BY' in sql:
            # Group by query
            rows = db.session.execute(text(sql), params).fetchall()
            result = [dict(row._mapping) for row in rows]
            return {
                'type': 'group',
                'data': result
            }
        else:
            # Row query
            rows = db.session.execute(text(sql), params).fetchall()
            result = [dict(row._mapping) for row in rows]
            return {
                'type': 'rows',
                'data': result
            }
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {
            'type': 'error',
            'data': str(e)
        }

def format_query_result(query_info: Dict[str, Any], query_result: Dict[str, Any]) -> str:
    """
    Format query result into a human-readable response.
    
    Args:
        query_info: Dictionary with query parameters
        query_result: Dictionary with query results
        
    Returns:
        Formatted string response
    """
    if query_result['type'] == 'error':
        return f"Sorry, I encountered an error: {query_result['data']}"
    
    if query_info['query_type'] == 'category_total':
        category = query_info['params']['category'].replace('%', '')
        amount = query_result['data']
        
        if 'start_date' in query_info['params'] and 'end_date' in query_info['params']:
            time_range = f" from {query_info['params']['start_date']} to {query_info['params']['end_date']}"
        else:
            time_range = ""
            
        return f"You spent ${amount:.2f} on {category}{time_range}."
    
    elif query_info['query_type'] == 'timeframe_total':
        timeframe = query_info['params']['timeframe']
        amount = query_result['data']
        return f"You spent ${amount:.2f} in the {timeframe}."
    
    elif query_info['query_type'] == 'category_in_timeframe':
        category = query_info['params']['category'].replace('%', '')
        timeframe = query_info['params']['timeframe']
        amount = query_result['data']
        return f"You spent ${amount:.2f} on {category} in the {timeframe}."
    
    elif query_info['query_type'] == 'top_expenses':
        expenses = query_result['data']
        
        if not expenses:
            return "You don't have any expenses recorded."
        
        response = ["Your top expenses are:"]
        for i, expense in enumerate(expenses, 1):
            date_str = expense['date'].strftime('%Y-%m-%d') if 'date' in expense else 'Unknown date'
            amount = expense['amount'] if 'amount' in expense else 0
            category = expense['category'] if 'category' in expense else 'Uncategorized'
            description = expense['description'] if 'description' in expense else 'No description'
            
            response.append(f"{i}. ${amount:.2f} on {category} ({description}) - {date_str}")
        
        return "\n".join(response)
    
    elif query_info['query_type'] == 'category_comparison':
        categories = query_result['data']
        
        if not categories:
            return "You don't have any expenses recorded."
        
        total = sum(cat['total'] for cat in categories)
        
        response = ["Your spending by category:"]
        for category in categories:
            cat_name = category['category'] if 'category' in category else 'Uncategorized'
            amount = category['total'] if 'total' in category else 0
            percentage = (amount / total * 100) if total > 0 else 0
            
            response.append(f"- {cat_name}: ${amount:.2f} ({percentage:.1f}%)")
        
        return "\n".join(response)
    
    elif query_info['query_type'] == 'month_comparison':
        months = query_result['data']
        
        if not months:
            return "You don't have any expenses recorded."
        
        response = ["Your monthly spending:"]
        for month_data in months:
            year = int(month_data['year']) if 'year' in month_data else 0
            month = int(month_data['month']) if 'month' in month_data else 0
            amount = month_data['total'] if 'total' in month_data else 0
            
            month_name = datetime.date(year, month, 1).strftime('%B %Y')
            response.append(f"- {month_name}: ${amount:.2f}")
        
        return "\n".join(response)
    
    elif query_info['query_type'] == 'category_explosion':
        categories = query_result['data']
        
        if not categories:
            return "There isn't enough data to compare spending across periods."
        
        # Find categories with significant increase
        significant_increases = []
        for cat in categories:
            if cat.get('percentage_change') and cat['percentage_change'] > 10:
                significant_increases.append({
                    'category': cat['category'],
                    'current': cat['current_total'],
                    'previous': cat['previous_total'] or 0,
                    'change': cat['percentage_change']
                })
        
        if not significant_increases:
            return "No categories have significantly increased in spending compared to the previous period."
        
        # Sort by percentage change
        significant_increases.sort(key=lambda x: x['change'], reverse=True)
        
        # Get the top increase
        top_increase = significant_increases[0]
        
        return f"The category with the biggest increase is '{top_increase['category']}' with a {top_increase['change']:.1f}% increase (from ${top_increase['previous']:.2f} to ${top_increase['current']:.2f})."
    
    return "I'm not sure how to answer that question."

def generate_ai_response(query_text: str, user_id: int) -> str:
    """
    Generate a response for unmatched queries using AI.
    
    Args:
        query_text: User's natural language query
        user_id: User ID
        
    Returns:
        AI-generated response string
    """
    # Handle common general questions without using OpenAI
    query_lower = query_text.lower().strip()
    
    # Basic FAQ responses
    if "what is your name" in query_lower or "who are you" in query_lower:
        return "I'm your financial assistant. I'm designed to help you understand your expenses and spending patterns."
    
    if "hello" in query_lower or "hi " in query_lower or query_lower == "hi":
        return "Hello! I'm your financial assistant. You can ask me about your expenses, spending patterns, or get insights on your financial data."
    
    if "how are you" in query_lower:
        return "I'm functioning well, thank you! I'm here to help you with your financial questions. Feel free to ask about your expenses or spending habits."
    
    if "help" in query_lower or "what can you do" in query_lower:
        return "I can help you understand your spending patterns, track expenses by category, compare monthly spending, identify unusual expenses, and forecast future spending. Try asking questions like 'How much did I spend on food last month?' or 'What were my top 5 expenses?'"
    
    if "thank" in query_lower:
        return "You're welcome! I'm happy to assist with your financial questions. Is there anything else you'd like to know about your expenses?"
    
    if "bye" in query_lower or "goodbye" in query_lower:
        return "Goodbye! Feel free to come back anytime you need insights on your finances."
    
    # If OpenAI API is not available or we have no client
    if not openai_client:
        return "I'm designed to answer questions about your financial data. For questions about your expenses, try something like 'How much did I spend on food?' or 'What were my top expenses?'"
    
    # If it's a more complex or non-financial question, try to use OpenAI if available
    try:
        # Get some recent expenses to provide context
        expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).limit(20).all()
        
        # Format expense data
        expense_data = []
        for e in expenses:
            expense_data.append({
                'date': e.date.strftime('%Y-%m-%d'),
                'description': e.description,
                'category': e.category,
                'amount': e.amount
            })
        
        # Get summary of expenses
        total_amount = sum(e.amount for e in expenses)
        categories = {}
        for e in expenses:
            if e.category not in categories:
                categories[e.category] = 0
            categories[e.category] += e.amount
        
        # Format category data
        category_data = []
        for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            category_data.append({
                'category': cat,
                'amount': amount,
                'percentage': (amount / total_amount * 100) if total_amount > 0 else 0
            })
        
        # Create prompt
        prompt = f"""
        I'm a user asking about my expenses. Here's my question:
        
        "{query_text}"
        
        Here's recent expense data to help answer my question:
        
        Total recent expenses: ${total_amount:.2f}
        
        Top spending categories:
        {json.dumps(category_data, indent=2)}
        
        Recent expenses:
        {json.dumps(expense_data, indent=2)}
        
        Please provide a helpful, conversational response focused specifically on answering my question based on the expense data. Keep it brief (2-3 sentences max).
        """
        
        # Generate response from OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful financial assistant that provides insights about expenses."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return "I'm designed to answer financial questions about your expenses. Try asking something like 'How much did I spend on food last month?' or 'What were my top expenses?'"

def process_query(query_text: str) -> dict:
    """
    Process a natural language query and return a response.
    
    Args:
        query_text: User's natural language query
        
    Returns:
        Dictionary with response and metadata
    """
    if not current_user or not current_user.is_authenticated:
        return {"success": False, "response": "Please log in to use the conversation assistant."}
    
    try:
        # Analyze query to determine type and parameters
        query_info = analyze_query(query_text)
        
        if query_info['query_type'] == 'unmatched':
            # Use AI to generate a response
            response = generate_ai_response(query_text, current_user.id)
            return {"success": True, "response": response, "query_type": "ai_generated"}
        
        # Execute the SQL query
        query_result = execute_query(query_info)
        
        # Format the result
        response = format_query_result(query_info, query_result)
        
        # Add a helpful tip based on the query type
        tip = get_helpful_tip(query_info, query_result)
        if tip:
            response += f"\n\n💡 {tip}"
        
        return {
            "success": True, 
            "response": response, 
            "query_type": query_info['query_type'],
            "data": query_result
        }
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {"success": False, "response": f"Sorry, I encountered an error processing your question. Please try another question or rephrase it."}

def get_helpful_tip(query_info: Dict[str, Any], query_result: Dict[str, Any]) -> str:
    """
    Generate a helpful tip based on the query type and result.
    
    Args:
        query_info: Information about the query
        query_result: Results from the query
        
    Returns:
        A helpful tip or empty string if no tip is applicable
    """
    import random  # Import here to avoid global import issues
    
    query_type = query_info['query_type']
    
    # Tips for expense queries
    if query_type == 'expense_total':
        category = query_info.get('category')
        if category and query_result.get('total', 0) > 500:
            return f"Your spending on {category} is quite high. Consider setting a budget limit for this category."
    
    elif query_type == 'top_expenses':
        if query_result.get('expenses') and len(query_result['expenses']) > 0:
            top_expense = query_result['expenses'][0]
            return f"Your highest expense was on {top_expense['description']}. Is this a one-time purchase or a recurring expense?"
    
    elif query_type == 'category_comparison':
        categories = query_result.get('categories', [])
        if categories and len(categories) > 1:
            top_category = max(categories, key=lambda x: x['amount'])
            percentage = top_category['percentage']
            if percentage > 40:
                return f"Your {top_category['category']} expenses make up {percentage:.1f}% of your total spending. Diversifying your spending can help maintain financial balance."
    
    elif query_type == 'spending_trend':
        trend = query_result.get('trend')
        if trend == 'increasing':
            return "Your spending is trending upward. Review your recent expenses to identify areas where you could cut back."
        elif trend == 'decreasing':
            return "Great job! Your spending is trending downward. Keep up the good financial habits."
    
    # Default tips based on random selection
    default_tips = [
        "Tracking your expenses regularly can help you stay within budget.",
        "Consider setting aside money for savings each month before spending on non-essentials.",
        "Comparing your expenses month-to-month can help identify unusual spending patterns.",
        "Try creating categories for your expenses to better understand your spending habits.",
        "Setting automatic transfers to savings can help build your emergency fund without thinking about it."
    ]
    
    # Return a random tip 20% of the time if no specific tip was generated
    if random.random() < 0.2:
        return random.choice(default_tips)
    
    return ""
"""
Implementation of time-series forecasting for predicting future expenses.
"""

def get_last_month_predictions(user_id: int) -> Dict[str, Any]:
    """
    Generate detailed predictions based specifically on last month's expenses.
    
    This function provides a detailed breakdown of last month's expenses by category
    and predicts spending for the current month based on recent patterns.
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with last month analysis and predictions
    """
    # Get the current and last month dates
    today = datetime.datetime.now()
    current_month = datetime.date(today.year, today.month, 1)
    
    # Calculate last month
    if today.month == 1:
        last_month = datetime.date(today.year - 1, 12, 1)
    else:
        last_month = datetime.date(today.year, today.month - 1, 1)
    
    # Last month end date
    if last_month.month == 12:
        last_month_end = datetime.date(last_month.year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_month_end = datetime.date(last_month.year, last_month.month + 1, 1) - datetime.timedelta(days=1)
    
    # Get last month's expenses by category
    last_month_sql = """
    SELECT category, SUM(amount) as total
    FROM expenses
    WHERE user_id = :user_id
    AND date >= :start_date
    AND date <= :end_date
    GROUP BY category
    ORDER BY total DESC
    """
    
    params = {
        'user_id': user_id,
        'start_date': last_month,
        'end_date': last_month_end
    }
    
    last_month_categories = db.session.execute(text(last_month_sql), params).all()
    
    # Get total expenses for last month
    last_month_total_sql = """
    SELECT SUM(amount) as total
    FROM expenses
    WHERE user_id = :user_id
    AND date >= :start_date
    AND date <= :end_date
    """
    
    last_month_total_result = db.session.execute(text(last_month_total_sql), params).first()
    last_month_total = float(last_month_total_result.total) if last_month_total_result.total else 0
    
    # Format category data
    category_data = []
    for cat in last_month_categories:
        category_data.append({
            'category': cat.category,
            'total': float(cat.total),
            'percentage': round((float(cat.total) / last_month_total * 100), 1) if last_month_total > 0 else 0
        })
    
    # Get daily spending patterns for last month
    daily_sql = """
    SELECT date, SUM(amount) as total
    FROM expenses
    WHERE user_id = :user_id
    AND date >= :start_date
    AND date <= :end_date
    GROUP BY date
    ORDER BY date
    """
    
    daily_expenses = db.session.execute(text(daily_sql), params).all()
    
    # Format daily data
    daily_data = []
    for day in daily_expenses:
        daily_data.append({
            'date': day.date.strftime('%Y-%m-%d'),
            'total': float(day.total)
        })
    
    # Calculate predictions for the current month based on last month's patterns
    predicted_categories = []
    for cat in category_data:
        # Predict slight increase based on general inflation and spending trends
        predicted_amount = cat['total'] * 1.025  # Assume 2.5% increase
        
        predicted_categories.append({
            'category': cat['category'],
            'last_month': cat['total'],
            'predicted': round(predicted_amount, 2),
            'change': round((predicted_amount - cat['total']) / cat['total'] * 100, 1) if cat['total'] > 0 else 0
        })
    
    # Get user's budget to identify potential overages
    budget_categories = {}
    user = User.query.get(user_id)
    
    if user and hasattr(user, 'budget') and user.budget:
        # Get standard budget categories
        budget_categories = {
            'food': user.budget.food if user.budget.food else 0,
            'transportation': user.budget.transportation if user.budget.transportation else 0,
            'entertainment': user.budget.entertainment if user.budget.entertainment else 0,
            'bills': user.budget.bills if user.budget.bills else 0,
            'shopping': user.budget.shopping if user.budget.shopping else 0,
            'other': user.budget.other if user.budget.other else 0
        }
        
        # Add custom categories if they exist
        custom_categories = CustomBudgetCategory.query.filter_by(user_id=user_id).all()
        for custom in custom_categories:
            budget_categories[custom.name.lower()] = custom.amount
    
    # Check for potential budget overages based on predictions
    budget_alerts = []
    for pred in predicted_categories:
        category = pred['category'].lower()
        if category in budget_categories and budget_categories[category] > 0:
            if pred['predicted'] > budget_categories[category]:
                overage_percent = (pred['predicted'] - budget_categories[category]) / budget_categories[category] * 100
                budget_alerts.append({
                    'category': pred['category'],
                    'budget': budget_categories[category],
                    'predicted': pred['predicted'],
                    'overage_percent': round(overage_percent, 1)
                })
    
    # Prepare response
    return {
        'success': True,
        'message': 'Last month predictions generated successfully',
        'data': {
            'month_name': last_month.strftime('%B %Y'),
            'total_spent': last_month_total,
            'categories': category_data,
            'daily_spending': daily_data,
            'predictions': {
                'categories': predicted_categories,
                'total': round(sum(pred['predicted'] for pred in predicted_categories), 2),
                'budget_alerts': budget_alerts
            }
        }
    }

def get_expense_forecast(user_id: int, category: str = None, months_ahead: int = 3) -> Dict[str, Any]:
    """
    Generate expense forecast for a user.
    
    Args:
        user_id: User ID
        category: Optional category to filter by
        months_ahead: Number of months to forecast
        
    Returns:
        Dictionary with forecast data
    """
    # Get historical expense data using raw SQL to avoid table name issues
    sql_query = """
    SELECT EXTRACT(YEAR FROM date) as year, 
           EXTRACT(MONTH FROM date) as month,
           SUM(amount) as total
    FROM expenses
    WHERE user_id = :user_id
    """
    
    params = {'user_id': user_id}
    
    if category:
        sql_query += " AND category = :category"
        params['category'] = category
    
    sql_query += """
    GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
    ORDER BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
    """
    
    monthly_expenses = db.session.execute(text(sql_query), params).all()
    
    # Need at least 3 months of data for meaningful forecasting
    if len(monthly_expenses) < 3:
        return {
            'success': False,
            'message': 'Not enough historical data for forecasting. Need at least 3 months of data.',
            'data': None
        }
    
    # Format historical data
    historical_data = []
    for data in monthly_expenses:
        year = int(data.year)
        month = int(data.month)
        date = datetime.date(year, month, 1)
        
        historical_data.append({
            'date': date.strftime('%Y-%m'),
            'total': float(data.total)
        })
    
    # Use simple moving average for forecasting
    # Calculate the average monthly change
    changes = []
    for i in range(1, len(historical_data)):
        prev_total = historical_data[i-1]['total']
        curr_total = historical_data[i]['total']
        
        if prev_total > 0:
            change = (curr_total - prev_total) / prev_total
            changes.append(change)
    
    if not changes:
        avg_change = 0
    else:
        avg_change = sum(changes) / len(changes)
    
    # Get the last known month's expenses
    last_month_data = historical_data[-1]
    last_month_date = datetime.datetime.strptime(last_month_data['date'], '%Y-%m')
    last_month_total = last_month_data['total']
    
    # Generate forecast
    forecast_data = []
    current_total = last_month_total
    current_date = last_month_date
    
    for i in range(months_ahead):
        # Move to next month
        if current_date.month == 12:
            next_month_date = datetime.date(current_date.year + 1, 1, 1)
        else:
            next_month_date = datetime.date(current_date.year, current_date.month + 1, 1)
        
        # Calculate forecasted total
        next_month_total = current_total * (1 + avg_change)
        
        forecast_data.append({
            'date': next_month_date.strftime('%Y-%m'),
            'total': round(next_month_total, 2)
        })
        
        # Update current values for next iteration
        current_date = next_month_date
        current_total = next_month_total
    
    # Calculate savings depletion date if current rate continues
    if avg_change > 0:
        # If expenses are increasing, estimate when savings would be depleted
        # For simplicity, assume current savings and average monthly income
        
        # Get user's preference to find savings amount (if any)
        user = User.query.get(user_id)
        
        savings_amount = 5000  # Default assumption
        monthly_income = 4000  # Default assumption
        
        if user and user.preference:
            if user.preference.savings_amount:
                savings_amount = user.preference.savings_amount
            if user.preference.monthly_income:
                monthly_income = user.preference.monthly_income
        
        # Latest monthly expense
        latest_expense = last_month_total
        
        # Calculate monthly deficit/surplus
        monthly_balance = monthly_income - latest_expense
        
        if monthly_balance < 0:
            # There's a deficit
            months_until_depletion = savings_amount / abs(monthly_balance)
            depletion_date = last_month_date + datetime.timedelta(days=30 * months_until_depletion)
            
            depletion_info = {
                'date': depletion_date.strftime('%B %Y'),
                'months': round(months_until_depletion, 1)
            }
        else:
            depletion_info = None
    else:
        depletion_info = None
    
    return {
        'success': True,
        'message': 'Forecast generated successfully',
        'data': {
            'historical': historical_data,
            'forecast': forecast_data,
            'avg_monthly_change': avg_change * 100,  # Convert to percentage
            'depletion': depletion_info
        }
    }