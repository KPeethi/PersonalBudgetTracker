"""
Suggestions module for the Expense Tracker application.
Provides smart suggestions based on user spending patterns.
"""

from datetime import datetime, timedelta
import calendar
import logging

logger = logging.getLogger(__name__)

def generate_spending_suggestions(expenses, current_user_id=None):
    """
    Generate smart suggestions based on expense data.
    
    Args:
        expenses: List of expense objects
        current_user_id: ID of the current user (for filtering)
        
    Returns:
        Dictionary containing various suggestions
    """
    if not expenses:
        return {
            "has_suggestions": False,
            "message": "Add more expenses to get personalized suggestions."
        }
    
    # Filter expenses if user_id is provided
    if current_user_id:
        expenses = [exp for exp in expenses if exp.user_id == current_user_id]
    
    if not expenses:
        return {
            "has_suggestions": False,
            "message": "Add more expenses to get personalized suggestions."
        }
    
    # Calculate relevant date ranges
    today = datetime.today().date()
    first_day_current_month = datetime(today.year, today.month, 1).date()
    
    # Previous month
    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year
    
    first_day_prev_month = datetime(prev_year, prev_month, 1).date()
    last_day_prev_month = datetime(
        prev_year, 
        prev_month, 
        calendar.monthrange(prev_year, prev_month)[1]
    ).date()
    
    # Filter expenses by month
    current_month_expenses = [exp for exp in expenses if exp.date >= first_day_current_month]
    prev_month_expenses = [exp for exp in expenses if first_day_prev_month <= exp.date <= last_day_prev_month]
    
    # Calculate totals
    total_current_month = sum(exp.amount for exp in current_month_expenses)
    total_prev_month = sum(exp.amount for exp in prev_month_expenses)
    
    # Get category breakdowns
    prev_month_by_category = {}
    for expense in prev_month_expenses:
        if expense.category not in prev_month_by_category:
            prev_month_by_category[expense.category] = 0
        prev_month_by_category[expense.category] += expense.amount
    
    current_month_by_category = {}
    for expense in current_month_expenses:
        if expense.category not in current_month_by_category:
            current_month_by_category[expense.category] = 0
        current_month_by_category[expense.category] += expense.amount
    
    # Generate suggestions
    suggestions = {
        "has_suggestions": True,
        "spending_trends": [],
        "savings_opportunities": [],
        "budget_recommendations": []
    }
    
    # 1. Spending trend analysis
    if total_prev_month > 0:
        if total_current_month > total_prev_month:
            percent_increase = ((total_current_month - total_prev_month) / total_prev_month) * 100
            suggestions["spending_trends"].append(
                f"Your spending is up {percent_increase:.1f}% compared to last month."
            )
        else:
            percent_decrease = ((total_prev_month - total_current_month) / total_prev_month) * 100
            suggestions["spending_trends"].append(
                f"You've reduced spending by {percent_decrease:.1f}% compared to last month. Great job!"
            )
    
    # 2. Category-specific insights
    for category, amount in prev_month_by_category.items():
        current_amount = current_month_by_category.get(category, 0)
        
        # Only show significant changes (>20%)
        if amount > 0 and abs(current_amount - amount) / amount > 0.2:
            if current_amount > amount:
                percent_increase = ((current_amount - amount) / amount) * 100
                suggestions["spending_trends"].append(
                    f"{category}: Spending increased by {percent_increase:.1f}% compared to last month."
                )
            else:
                percent_decrease = ((amount - current_amount) / amount) * 100
                suggestions["spending_trends"].append(
                    f"{category}: Spending decreased by {percent_decrease:.1f}% compared to last month."
                )
    
    # 3. Identify top spending categories
    if prev_month_by_category:
        sorted_categories = sorted(prev_month_by_category.items(), key=lambda x: x[1], reverse=True)
        top_categories = sorted_categories[:3]
        
        for category, amount in top_categories:
            percent_of_total = (amount / total_prev_month) * 100
            if percent_of_total > 20:  # Only suggest if it's a significant part of spending
                suggestions["savings_opportunities"].append(
                    f"Last month, {percent_of_total:.1f}% of your spending was on {category}. "
                    f"Consider setting a budget for this category."
                )
    
    # 4. Budget recommendations
    if prev_month_expenses:
        avg_daily_spending = total_prev_month / (last_day_prev_month - first_day_prev_month + timedelta(days=1)).days
        suggestions["budget_recommendations"].append(
            f"Based on your spending, a daily budget of ${avg_daily_spending:.2f} would match your previous month's habits."
        )
    
    # 5. Monthly budget
    days_in_current_month = calendar.monthrange(today.year, today.month)[1]
    suggested_monthly_budget = total_prev_month * 0.9  # Suggest 10% less than last month
    suggestions["budget_recommendations"].append(
        f"Suggested monthly budget: ${suggested_monthly_budget:.2f} (10% less than last month)"
    )
    
    # No suggestions case
    if not suggestions["spending_trends"] and not suggestions["savings_opportunities"] and not suggestions["budget_recommendations"]:
        suggestions["has_suggestions"] = False
        suggestions["message"] = "Add more varied expense data to get personalized suggestions."
    
    return suggestions