"""
AI Assistant module for the Expense Tracker application.
Provides intelligent analysis and recommendations based on expense data.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import calendar

from openai import OpenAI

# Import configuration
from config import OPENAI_API_KEY, OPENAI_MODEL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# AI Analysis Options
ANALYSIS_OPTIONS = {
    "expense_trends": {
        "title": "Expense Trend Analysis",
        "description": "Identify spending patterns and trends over time.",
        "prompt_template": """
            Analyze the following expense data over time:
            {expense_data}
            
            Focus on:
            1. Monthly/weekly spending trends
            2. Irregular spending patterns
            3. Notable increases or decreases in specific categories
            4. Seasonal patterns if applicable
            
            Provide a clear, concise analysis with actionable insights in a friendly, conversational tone.
            Limit your response to 3-5 key observations and make them specific to the data.
        """
    },
    "budget_recommendations": {
        "title": "Budget Recommendations",
        "description": "Get personalized budget suggestions based on your spending history.",
        "prompt_template": """
            Based on the following expense data:
            {expense_data}
            
            Total expenses: ${total_expenses}
            Income (if available): ${income}
            
            Provide specific budget recommendations including:
            1. Suggested spending limits for top 3 categories
            2. Areas where spending could be reduced
            3. A balanced monthly budget breakdown
            4. Specific, actionable advice for better financial management
            
            Make recommendations practical, personalized, and based on the actual spending patterns in the data.
            Write in a supportive, non-judgmental tone. Limit to 5 key recommendations.
        """
    },
    "savings_opportunities": {
        "title": "Savings Opportunities",
        "description": "Discover potential savings based on your spending patterns.",
        "prompt_template": """
            Analyze these expenses to find savings opportunities:
            {expense_data}
            
            Identify:
            1. Categories with unusually high spending
            2. Potential subscription overlaps or unused services
            3. Timing opportunities (e.g., bulk purchases, seasonal buying)
            4. Specific items or services where cheaper alternatives might exist
            
            For each opportunity, provide an estimated potential monthly savings amount.
            Be specific and practical in your advice. Limit to 3-4 concrete suggestions.
        """
    },
    "category_analysis": {
        "title": "Category Spending Analysis",
        "description": "Deep dive into your spending categories to identify patterns and outliers.",
        "prompt_template": """
            Analyze the following expense categories:
            {category_data}
            
            For each major category:
            1. Compare to typical household spending benchmarks
            2. Identify subcategory patterns
            3. Highlight any unusual or concerning spending
            4. Note positive spending habits
            
            Provide specific insights about the user's unique category distribution.
            Be objective and analytical but maintain a helpful, conversational tone.
        """
    },
    "financial_goals": {
        "title": "Financial Goal Setting",
        "description": "Get customized financial goal suggestions based on your spending history.",
        "prompt_template": """
            Based on the following expense history:
            {expense_data}
            
            Suggest 3 personalized financial goals including:
            1. A specific savings target with timeline
            2. A spending reduction goal for the highest category
            3. A debt reduction plan if applicable
            
            For each goal, provide:
            - A clear target amount
            - A realistic timeframe
            - Specific action steps to achieve it
            - A way to measure progress
            
            Make all goals SMART (Specific, Measurable, Achievable, Relevant, Time-bound).
            Write in a motivational and encouraging tone.
        """
    }
}


def format_expense_data_for_ai(expenses: List[Dict[str, Any]], 
                               include_time_info: bool = True,
                               include_detailed_breakdown: bool = True) -> str:
    """
    Format expense data in a structured way for AI analysis.
    
    Args:
        expenses: List of Expense objects or dictionaries
        include_time_info: Whether to include time-based aggregations
        include_detailed_breakdown: Whether to include detailed expense entries
        
    Returns:
        A formatted string representation of expense data
    """
    if not expenses:
        return "No expense data available."
    
    # Calculate basic statistics
    total_spent = sum(expense['amount'] for expense in expenses)
    avg_expense = total_spent / len(expenses) if expenses else 0
    
    # Get date range
    dates = [expense['date'] for expense in expenses if isinstance(expense['date'], datetime)]
    if dates:
        min_date = min(dates)
        max_date = max(dates)
        date_range = f"From {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
    else:
        date_range = "Unknown date range"
    
    # Categorize expenses
    categories = {}
    for expense in expenses:
        category = expense['category']
        if category not in categories:
            categories[category] = 0
        categories[category] += expense['amount']
    
    # Sort categories by amount (highest first)
    sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    
    # Build formatted string
    result = [
        f"Expense Summary:",
        f"- Total spent: ${total_spent:.2f}",
        f"- Number of expenses: {len(expenses)}",
        f"- Average expense: ${avg_expense:.2f}",
        f"- {date_range}",
        f"\nCategory Breakdown:"
    ]
    
    for category, amount in sorted_categories:
        percentage = (amount / total_spent) * 100 if total_spent > 0 else 0
        result.append(f"- {category}: ${amount:.2f} ({percentage:.1f}%)")
    
    # Add time-based analysis if requested
    if include_time_info and expenses:
        result.append("\nMonthly Analysis:")
        monthly_data = {}
        
        for expense in expenses:
            expense_date = expense['date']
            if isinstance(expense_date, datetime):
                month_key = expense_date.strftime("%Y-%m")
                if month_key not in monthly_data:
                    monthly_data[month_key] = 0
                monthly_data[month_key] += expense['amount']
        
        # Sort months chronologically
        sorted_months = sorted(monthly_data.items())
        for month_key, amount in sorted_months:
            result.append(f"- {month_key}: ${amount:.2f}")
    
    # Add detailed entries if requested
    if include_detailed_breakdown and expenses:
        result.append("\nRecent Expenses (up to 15):")
        # Sort by date (newest first)
        sorted_expenses = sorted(expenses, key=lambda x: x['date'] if isinstance(x['date'], datetime) else datetime.min, reverse=True)
        
        # Include up to 15 most recent expenses
        for i, expense in enumerate(sorted_expenses[:15]):
            expense_date = expense['date']
            date_str = expense_date.strftime("%Y-%m-%d") if isinstance(expense_date, datetime) else "Unknown date"
            result.append(f"- {date_str}: {expense['description']} (${expense['amount']:.2f}, Category: {expense['category']})")
    
    return "\n".join(result)


def format_category_data_for_ai(expenses: List[Dict[str, Any]]) -> str:
    """
    Format category data for AI analysis.
    
    Args:
        expenses: List of Expense objects or dictionaries
        
    Returns:
        A formatted string with detailed category analysis
    """
    if not expenses:
        return "No expense data available."
    
    # Calculate total spent
    total_spent = sum(expense['amount'] for expense in expenses)
    
    # Create category map
    categories = {}
    for expense in expenses:
        category = expense['category']
        if category not in categories:
            categories[category] = {
                'total': 0,
                'count': 0,
                'expenses': []
            }
        
        categories[category]['total'] += expense['amount']
        categories[category]['count'] += 1
        categories[category]['expenses'].append({
            'date': expense['date'],
            'amount': expense['amount'],
            'description': expense['description']
        })
    
    # Build formatted string
    result = [
        f"Category Analysis:",
        f"- Total expenses: ${total_spent:.2f}",
        f"- Number of categories: {len(categories)}",
        f"\nDetailed Category Breakdown:"
    ]
    
    # Sort categories by total amount (highest first)
    sorted_categories = sorted(categories.items(), key=lambda x: x[1]['total'], reverse=True)
    
    for category_name, data in sorted_categories:
        percentage = (data['total'] / total_spent) * 100 if total_spent > 0 else 0
        avg_expense = data['total'] / data['count'] if data['count'] > 0 else 0
        
        result.append(f"\n{category_name}:")
        result.append(f"- Total spent: ${data['total']:.2f} ({percentage:.1f}% of all expenses)")
        result.append(f"- Number of expenses: {data['count']}")
        result.append(f"- Average per expense: ${avg_expense:.2f}")
        
        # Sort expenses by amount (highest first)
        sorted_expenses = sorted(data['expenses'], key=lambda x: x['amount'], reverse=True)
        
        # Show top 3 expenses in this category
        if sorted_expenses:
            result.append("- Top expenses in this category:")
            for idx, expense in enumerate(sorted_expenses[:3]):
                date_str = expense['date'].strftime("%Y-%m-%d") if isinstance(expense['date'], datetime) else "Unknown date"
                result.append(f"  {idx+1}. {expense['description']} - ${expense['amount']:.2f} ({date_str})")
    
    return "\n".join(result)


def get_analysis_options() -> Dict[str, Dict[str, str]]:
    """
    Get available AI analysis options.
    
    Returns:
        Dictionary of analysis options with titles and descriptions
    """
    options = {}
    for key, data in ANALYSIS_OPTIONS.items():
        options[key] = {
            'title': data['title'],
            'description': data['description']
        }
    return options


def generate_ai_analysis(analysis_type: str, 
                         expenses: List[Dict[str, Any]], 
                         income: Optional[float] = None) -> str:
    """
    Generate AI analysis based on expense data.
    
    Args:
        analysis_type: Type of analysis to perform (from ANALYSIS_OPTIONS)
        expenses: List of expense objects or dictionaries
        income: Monthly income amount (optional)
        
    Returns:
        String containing the AI analysis
    """
    if analysis_type not in ANALYSIS_OPTIONS:
        return f"Invalid analysis type: {analysis_type}. Available types: {', '.join(ANALYSIS_OPTIONS.keys())}"
    
    try:
        # Format expense data appropriately
        if analysis_type == "category_analysis":
            expense_data = format_category_data_for_ai(expenses)
        else:
            expense_data = format_expense_data_for_ai(expenses)
        
        # Get template and fill in data
        template = ANALYSIS_OPTIONS[analysis_type]['prompt_template']
        total_expenses = sum(expense['amount'] for expense in expenses)
        
        prompt = template.format(
            expense_data=expense_data,
            category_data=format_category_data_for_ai(expenses),
            total_expenses=f"{total_expenses:.2f}",
            income=f"{income:.2f}" if income is not None else "unknown"
        )
        
        # Generate response from OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful financial advisor specializing in personal expense analysis."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract and return the analysis
        analysis = response.choices[0].message.content
        return analysis
    
    except Exception as e:
        logger.exception(f"Error generating AI analysis: {e}")
        return f"Error generating analysis: {str(e)}"


def get_expense_insights(expenses: List[Dict[str, Any]], 
                         time_period: str = 'all') -> str:
    """
    Get general insights about expenses without requiring specific analysis type.
    
    Args:
        expenses: List of expense objects or dictionaries
        time_period: Time period to analyze ('all', 'month', 'year', etc.)
        
    Returns:
        String containing general expense insights
    """
    if not expenses:
        return "No expense data available for analysis."
    
    try:
        # Filter expenses by time period if needed
        filtered_expenses = expenses
        period_description = "all recorded expenses"
        
        if time_period == 'month':
            today = datetime.today()
            start_date = datetime(today.year, today.month, 1)
            end_date = datetime(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
            filtered_expenses = [e for e in expenses if isinstance(e['date'], datetime) and start_date <= e['date'] <= end_date]
            period_description = f"expenses in {today.strftime('%B %Y')}"
            
        elif time_period == 'year':
            today = datetime.today()
            start_date = datetime(today.year, 1, 1)
            end_date = datetime(today.year, 12, 31)
            filtered_expenses = [e for e in expenses if isinstance(e['date'], datetime) and start_date <= e['date'] <= end_date]
            period_description = f"expenses in {today.year}"
        
        # Format expense data
        expense_data = format_expense_data_for_ai(filtered_expenses)
        
        # Create prompt for general insights
        prompt = f"""
        Provide a brief overview of the following {period_description}:
        
        {expense_data}
        
        Focus on:
        1. The top 2-3 spending categories and what they might indicate
        2. Any unusual or noteworthy spending patterns
        3. 1-2 practical suggestions for improving financial health
        
        Keep your response concise (under 5 paragraphs), conversational and focused on actionable insights.
        """
        
        # Generate response from OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful financial advisor specializing in personal expense analysis."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract and return the insights
        insights = response.choices[0].message.content
        return insights
    
    except Exception as e:
        logger.exception(f"Error generating expense insights: {e}")
        return f"Error generating insights: {str(e)}"