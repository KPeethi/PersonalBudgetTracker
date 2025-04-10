"""
AI Assistant module for the Expense Tracker application.
Provides intelligent analysis and recommendations based on expense data.
"""

from datetime import datetime, timedelta
import logging
import os
import re
from typing import List, Dict, Any, Optional
import config

# Set up logging
logger = logging.getLogger(__name__)

# Import OpenAI
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or config.OPENAI_API_KEY
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_MODEL = config.OPENAI_MODEL
        logger.debug(f"OpenAI API configured with model: {OPENAI_MODEL}")
    else:
        openai_client = None
        logger.warning("OpenAI API key not configured")
except ImportError:
    openai_client = None
    logger.warning("OpenAI package not available")
except Exception as e:
    openai_client = None
    logger.error(f"Error initializing OpenAI: {str(e)}")

# Analysis options
ANALYSIS_OPTIONS = {
    "budget_analysis": {
        "title": "Budget Analysis",
        "description": "Analyze your spending relative to your income and recommend budget adjustments"
    },
    "category_analysis": {
        "title": "Category Analysis",
        "description": "Analyze spending patterns across different categories"
    },
    "trend_analysis": {
        "title": "Spending Trend Analysis",
        "description": "Identify trends in your spending habits over time"
    },
    "savings_opportunities": {
        "title": "Savings Opportunities",
        "description": "Identify areas where you could reduce spending to save more"
    },
    "financial_goals": {
        "title": "Financial Goals Planning",
        "description": "Get recommendations for achieving financial goals based on your spending patterns"
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
        return "No expense data available"
    
    # Calculate total amount
    total_amount = sum(expense.get('amount', 0) for expense in expenses)
    
    # Group by category
    categories = {}
    for expense in expenses:
        category = expense.get('category', 'Uncategorized')
        if category not in categories:
            categories[category] = 0
        categories[category] += expense.get('amount', 0)
    
    # Group by month if time info requested
    monthly_data = {}
    if include_time_info:
        for expense in expenses:
            date = expense.get('date')
            if isinstance(date, datetime):
                month_key = date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = 0
                monthly_data[month_key] += expense.get('amount', 0)
    
    # Format the output
    output = [f"Total Expenses: ${total_amount:.2f}"]
    output.append(f"Number of Expenses: {len(expenses)}")
    output.append(f"Number of Categories: {len(categories)}")
    output.append("\nCategory Breakdown:")
    
    for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_amount) * 100 if total_amount > 0 else 0
        output.append(f"- {category}: ${amount:.2f} ({percentage:.1f}%)")
    
    if include_time_info and monthly_data:
        output.append("\nMonthly Breakdown:")
        for month, amount in sorted(monthly_data.items()):
            output.append(f"- {month}: ${amount:.2f}")
    
    if include_detailed_breakdown:
        output.append("\nRecent Expenses:")
        # Sort expenses by date (newest first) and take the most recent 10
        recent_expenses = sorted(
            [exp for exp in expenses if exp.get('date')], 
            key=lambda x: x.get('date'), 
            reverse=True
        )[:10]
        
        for i, expense in enumerate(recent_expenses, 1):
            date_str = expense.get('date').strftime('%Y-%m-%d') if expense.get('date') else 'Unknown'
            output.append(f"{i}. {date_str} - {expense.get('category')}: ${expense.get('amount', 0):.2f} - {expense.get('description', 'No description')}")
    
    return "\n".join(output)

def format_category_data_for_ai(expenses: List[Dict[str, Any]]) -> str:
    """
    Format category data for AI analysis.
    
    Args:
        expenses: List of Expense objects or dictionaries
        
    Returns:
        A formatted string with detailed category analysis
    """
    if not expenses:
        return "No expense data available"
    
    # Group by category
    categories = {}
    for expense in expenses:
        category = expense.get('category', 'Uncategorized')
        if category not in categories:
            categories[category] = {
                'total': 0,
                'count': 0,
                'expenses': []
            }
        categories[category]['total'] += expense.get('amount', 0)
        categories[category]['count'] += 1
        categories[category]['expenses'].append(expense)
    
    # Calculate total amount
    total_amount = sum(data['total'] for data in categories.values())
    
    # Format the output
    output = [f"Category Analysis (Total: ${total_amount:.2f})"]
    
    for category, data in sorted(categories.items(), key=lambda x: x[1]['total'], reverse=True):
        percentage = (data['total'] / total_amount) * 100 if total_amount > 0 else 0
        avg_amount = data['total'] / data['count'] if data['count'] > 0 else 0
        
        output.append(f"\n## {category}")
        output.append(f"Total: ${data['total']:.2f} ({percentage:.1f}% of all expenses)")
        output.append(f"Number of Expenses: {data['count']}")
        output.append(f"Average Amount: ${avg_amount:.2f}")
        
        # Add sample expenses
        output.append("Sample Expenses:")
        sorted_expenses = sorted(data['expenses'], key=lambda x: x.get('amount', 0), reverse=True)
        for i, expense in enumerate(sorted_expenses[:5], 1):
            date_str = expense.get('date').strftime('%Y-%m-%d') if expense.get('date') else 'Unknown'
            output.append(f"{i}. {date_str}: ${expense.get('amount', 0):.2f} - {expense.get('description', 'No description')}")
    
    return "\n".join(output)

def get_analysis_options() -> Dict[str, Dict[str, str]]:
    """
    Get available AI analysis options.
    
    Returns:
        Dictionary of analysis options with titles and descriptions
    """
    return ANALYSIS_OPTIONS

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
    if not openai_client:
        return "AI analysis is not available. Please check your OpenAI API configuration."
    
    if not expenses:
        return "No expense data available for analysis."
    
    if analysis_type not in ANALYSIS_OPTIONS:
        return f"Invalid analysis type: {analysis_type}. Available types: {', '.join(ANALYSIS_OPTIONS.keys())}"
    
    try:
        # Format expense data appropriately
        if analysis_type == "category_analysis":
            formatted_data = format_category_data_for_ai(expenses)
        else:
            formatted_data = format_expense_data_for_ai(expenses)
        
        # Create prompt based on analysis type
        prompt = ""
        if analysis_type == "budget_analysis":
            if income:
                prompt = f"""
                Analyze the following expense data and provide budget recommendations based on an income of ${income:.2f} per month:
                
                {formatted_data}
                
                Please provide:
                1. An analysis of whether spending is sustainable relative to income
                2. Recommended budget allocations by category (as percentages of income)
                3. Specific advice for categories where spending may be too high
                
                Keep your response concise and actionable.
                """
            else:
                prompt = f"""
                Analyze the following expense data and provide budget recommendations:
                
                {formatted_data}
                
                Please provide:
                1. Analysis of spending patterns by category
                2. Recommended general budget allocations (as percentages)
                3. Specific advice for categories where spending may be too high
                
                Keep your response concise and actionable.
                """
        
        elif analysis_type == "category_analysis":
            prompt = f"""
            Analyze the following category breakdown of expenses:
            
            {formatted_data}
            
            Please provide:
            1. Insights into the spending distribution across categories
            2. Any categories that seem unusually high or low compared to typical patterns
            3. Recommendations for potential adjustments to category spending
            
            Keep your response concise and actionable.
            """
        
        elif analysis_type == "trend_analysis":
            prompt = f"""
            Analyze the following expense data for trends over time:
            
            {formatted_data}
            
            Please provide:
            1. Observations about spending patterns over time
            2. Any notable increases or decreases in spending
            3. Seasonal or cyclical patterns if apparent
            
            Keep your response concise and actionable.
            """
        
        elif analysis_type == "savings_opportunities":
            prompt = f"""
            Analyze the following expense data to identify savings opportunities:
            
            {formatted_data}
            
            Please provide:
            1. Specific categories where spending could potentially be reduced
            2. Practical strategies for reducing spending in these areas
            3. An estimate of potential monthly savings if recommendations are followed
            
            Keep your response concise and actionable.
            """
        
        elif analysis_type == "financial_goals":
            prompt = f"""
            Based on the following expense data, provide recommendations for financial goals:
            
            {formatted_data}
            
            Please provide:
            1. Suggested financial goals based on current spending patterns
            2. Recommended adjustments to spending to achieve these goals
            3. A rough timeline for achieving different financial milestones
            
            Keep your response concise and actionable.
            """
        
        # Generate response from OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful financial advisor specializing in personal expense analysis."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    
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
    
    # Filter expenses by time period if needed
    filtered_expenses = expenses
    period_description = "all recorded expenses"
    
    if time_period == 'month':
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
        filtered_expenses = [e for e in expenses if isinstance(e.get('date'), datetime) and start_date <= e.get('date') <= end_date]
        period_description = f"expenses in {today.strftime('%B %Y')}"
        
    elif time_period == 'year':
        today = datetime.now()
        start_date = datetime(today.year, 1, 1)
        end_date = datetime(today.year, 12, 31)
        filtered_expenses = [e for e in expenses if isinstance(e.get('date'), datetime) and start_date <= e.get('date') <= end_date]
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
    
    # Try to use OpenAI API if available
    if openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful financial advisor specializing in personal expense analysis."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating expense insights using OpenAI: {str(e)}")
            # Fall through to fallback insights
    
    # Fallback insights without API
    try:
        # Create helpful fallback insights based on the expense data
        if not filtered_expenses or len(filtered_expenses) == 0:
            return "No expense data available for the selected time period. Try selecting a different period or add more expenses."
        
        # Simple analysis without API
        categories = {}
        total_spend = 0
        
        for expense in filtered_expenses:
            cat = expense.get('category', 'Other')
            amount = expense.get('amount', 0)
            categories[cat] = categories.get(cat, 0) + amount
            total_spend += amount
        
        # Sort categories by amount
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        top_categories = sorted_cats[:3] if len(sorted_cats) >= 3 else sorted_cats
        
        insights = [
            f"Based on your spending data, here are some basic insights:",
            f"Total spending: ${total_spend:.2f}",
            f"Your top spending categories are:"
        ]
        
        for cat, amount in top_categories:
            percent = (amount / total_spend * 100) if total_spend > 0 else 0
            insights.append(f"- {cat}: ${amount:.2f} ({percent:.1f}%)")
        
        insights.append("\nRecommendations:")
        insights.append("1. Track your expenses regularly to maintain better financial control.")
        insights.append("2. Set up a monthly budget for each spending category.")
        insights.append("3. Consider setting aside 10-15% of your income for savings.")
        
        return "\n".join(insights)
    except Exception as e:
        logger.error(f"Error generating fallback expense insights: {str(e)}")
        return "Unable to generate insights at this time. Please try again later."