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
        OPENAI_MODEL = "gpt-4"  # Default model if not in config
except ImportError:
    openai_client = None
    logger.warning("OpenAI package not available")
    OPENAI_MODEL = "gpt-4"  # Default model if not in config
except Exception as e:
    openai_client = None
    logger.error(f"Error initializing OpenAI: {str(e)}")
    OPENAI_MODEL = "gpt-4"  # Default model if not in config

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
            key=lambda x: x.get('date') if x.get('date') is not None else datetime.min, 
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
        
        # Generate response from OpenAI if available
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
                logger.error(f"Error generating AI analysis with OpenAI API: {str(e)}")
                # Fall through to fallback
        
        # Fallback analysis without OpenAI API
        # Calculate total amount and categories
        total_amount = sum(expense.get('amount', 0) for expense in expenses)
        categories = {}
        for expense in expenses:
            category = expense.get('category', 'Uncategorized')
            if category not in categories:
                categories[category] = 0
            categories[category] += expense.get('amount', 0)
        
        # Sort categories by amount
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        # Create basic response based on analysis type
        response = [f"Analysis of your expenses (Total: ${total_amount:.2f})"]
        
        if analysis_type == "budget_analysis":
            response.append("\nBudget Recommendations:")
            
            # If income provided, check sustainability
            if income:
                if total_amount > income:
                    response.append(f"⚠️ Your monthly expenses (${total_amount:.2f}) exceed your income (${income:.2f}). This is not sustainable.")
                else:
                    savings = income - total_amount
                    savings_percent = (savings / income) * 100 if income > 0 else 0
                    response.append(f"✓ Your monthly expenses (${total_amount:.2f}) are within your income (${income:.2f}).")
                    response.append(f"You're saving approximately ${savings:.2f} per month ({savings_percent:.1f}% of income).")
            
            # Recommended category allocations
            response.append("\nRecommended Budget Allocations:")
            
            # Standard budget percentages
            standard_budget = {
                "Housing": 30,
                "Food": 15,
                "Transportation": 10,
                "Utilities": 10,
                "Healthcare": 10,
                "Entertainment": 5,
                "Savings": 15,
                "Miscellaneous": 5
            }
            
            for category, amount in sorted_cats[:5]:
                percent = (amount / total_amount) * 100 if total_amount > 0 else 0
                std_percent = standard_budget.get(category, 10)  # Default to 10% if not in standard categories
                
                if percent > std_percent * 1.5:  # If spending 50% more than recommended
                    response.append(f"- {category}: ${amount:.2f} ({percent:.1f}% of total) - ⚠️ Consider reducing (recommended: {std_percent}%)")
                else:
                    response.append(f"- {category}: ${amount:.2f} ({percent:.1f}% of total)")
        
        elif analysis_type == "category_analysis":
            response.append("\nCategory Breakdown:")
            
            for category, amount in sorted_cats:
                percent = (amount / total_amount) * 100 if total_amount > 0 else 0
                response.append(f"- {category}: ${amount:.2f} ({percent:.1f}% of total)")
            
            # Add insights based on largest category
            if sorted_cats:
                top_category, top_amount = sorted_cats[0]
                top_percent = (top_amount / total_amount) * 100 if total_amount > 0 else 0
                
                if top_percent > 40:
                    response.append(f"\nInsight: Your {top_category} expenses represent a significant portion ({top_percent:.1f}%) of your total spending.")
                    response.append(f"Consider examining this category for potential savings opportunities.")
        
        elif analysis_type == "savings_opportunities":
            response.append("\nPotential Savings Opportunities:")
            
            # Look for categories with high spending
            for category, amount in sorted_cats[:3]:
                percent = (amount / total_amount) * 100 if total_amount > 0 else 0
                
                # Suggest specific strategies based on category
                if category.lower() in ["food", "dining", "restaurants", "groceries"]:
                    response.append(f"- {category} (${amount:.2f}, {percent:.1f}% of total):")
                    response.append("  • Meal planning and bulk cooking can reduce costs by 20-30%")
                    response.append("  • Limiting dining out to once per week can save $100-200 monthly")
                
                elif category.lower() in ["entertainment", "subscriptions", "streaming"]:
                    response.append(f"- {category} (${amount:.2f}, {percent:.1f}% of total):")
                    response.append("  • Review and cancel unused subscriptions")
                    response.append("  • Consider sharing subscription costs with family/friends")
                
                elif category.lower() in ["transportation", "gas", "fuel", "car"]:
                    response.append(f"- {category} (${amount:.2f}, {percent:.1f}% of total):")
                    response.append("  • Carpooling or public transportation can reduce costs by 40-50%")
                    response.append("  • Combining errands can reduce fuel consumption")
                
                else:
                    response.append(f"- {category} (${amount:.2f}, {percent:.1f}% of total):")
                    response.append("  • Review this category for non-essential spending")
                    response.append("  • Consider setting a monthly budget for this category")
        
        elif analysis_type == "trend_analysis" or analysis_type == "financial_goals":
            response.append("\nBasic Analysis:")
            
            for category, amount in sorted_cats[:5]:
                percent = (amount / total_amount) * 100 if total_amount > 0 else 0
                response.append(f"- {category}: ${amount:.2f} ({percent:.1f}% of total)")
            
            response.append("\nRecommendations:")
            response.append("1. Track your expenses regularly to identify trends over time")
            response.append("2. Set up a monthly budget for each category")
            response.append("3. Aim to save at least 15-20% of your income")
            response.append("4. Consider creating an emergency fund of 3-6 months of expenses")
        
        return "\n".join(response)
    
    except Exception as e:
        logger.exception(f"Error generating AI analysis: {e}")
        return f"Error generating analysis: {str(e)}"

def generate_expense_insights_fallback(expenses: List[Dict[str, Any]], period_description: str) -> str:
    """
    Generate expense insights without using OpenAI API.
    This is a fallback method when the API is unavailable or has errors.
    
    Args:
        expenses: List of filtered expense objects or dictionaries
        period_description: Description of the time period analyzed
        
    Returns:
        String containing manually generated insights
    """
    if not expenses:
        return "No expense data available for analysis."
    
    # Calculate total amount
    total_amount = sum(expense.get('amount', 0) for expense in expenses)
    
    # Group by category
    categories = {}
    for expense in expenses:
        category = expense.get('category', 'Uncategorized')
        if category not in categories:
            categories[category] = 0
        categories[category] += expense.get('amount', 0)
    
    # Get top categories
    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Calculate average per expense
    avg_amount = total_amount / len(expenses) if expenses else 0
    
    # Build response
    insights = [
        f"Based on your {period_description}, you've spent a total of ${total_amount:.2f} across {len(expenses)} transactions.",
        f"Your average expense is ${avg_amount:.2f}."
    ]
    
    # Top categories insights
    if top_categories:
        insights.append("\nYour top spending categories are:")
        for i, (category, amount) in enumerate(top_categories, 1):
            percentage = (amount / total_amount) * 100 if total_amount > 0 else 0
            insights.append(f"{i}. {category}: ${amount:.2f} ({percentage:.1f}% of total)")
    
    # General recommendation based on top category
    if top_categories:
        top_category, top_amount = top_categories[0]
        percentage = (top_amount / total_amount) * 100 if total_amount > 0 else 0
        
        if percentage > 50:
            insights.append(f"\nNote that {top_category} represents over half of your spending. Consider setting a budget for this category to better manage your finances.")
        elif percentage > 30:
            insights.append(f"\nYour spending in {top_category} is significant. Consider looking for ways to reduce costs in this area.")
        else:
            insights.append("\nYour spending appears to be fairly distributed among categories, which is generally a good sign for financial health.")
    
    # General suggestion
    insights.append("\nSuggestion: Track your expenses consistently to identify patterns and opportunities for saving. Consider setting category-specific budgets for better financial control.")
    
    return "\n".join(insights)

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
    
    try:
        if time_period == 'month':
            today = datetime.now()
            start_date = datetime(today.year, today.month, 1)
            if today.month == 12:
                end_date = datetime(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
            filtered_expenses = [e for e in expenses if isinstance(e.get('date'), datetime) and 
                                 e.get('date') is not None and 
                                 start_date <= e.get('date') <= end_date]
            period_description = f"expenses in {today.strftime('%B %Y')}"
            
        elif time_period == 'year':
            today = datetime.now()
            start_date = datetime(today.year, 1, 1)
            end_date = datetime(today.year, 12, 31)
            filtered_expenses = [e for e in expenses if isinstance(e.get('date'), datetime) and 
                                 e.get('date') is not None and 
                                 start_date <= e.get('date') <= end_date]
            period_description = f"expenses in {today.year}"
    except Exception as e:
        logger.error(f"Error filtering expenses by time period: {str(e)}")
        # Fall back to all expenses if there's an error
        filtered_expenses = expenses
        period_description = "all recorded expenses"
    
    # Format expense data
    try:
        expense_data = format_expense_data_for_ai(filtered_expenses)
    except Exception as e:
        logger.error(f"Error formatting expense data: {str(e)}")
        return f"Error formatting expense data: {str(e)}"
    
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
            # Use fallback if OpenAI API fails
            return generate_expense_insights_fallback(filtered_expenses, period_description)
    
    # If no OpenAI client or if API call failed, use fallback implementation
    return generate_expense_insights_fallback(filtered_expenses, period_description)