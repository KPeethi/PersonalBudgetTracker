"""
Expense Forecasting module for the Expense Tracker application.
Provides prediction models for forecasting future expenses.
"""

import datetime
import os
import logging
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import text
from models import User, db, CustomBudgetCategory

# Set up logging
logger = logging.getLogger(__name__)

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
    logger.debug(f"Generating last month predictions for user ID: {user_id}")
    
    # Get current date and determine last month
    today = datetime.date.today()
    logger.debug(f"Current date: {today}")
    
    # Last month date range
    if today.month == 1:
        last_month = 12
        last_month_year = today.year - 1
    else:
        last_month = today.month - 1
        last_month_year = today.year
    
    last_month_start = datetime.date(last_month_year, last_month, 1)
    if last_month == 12:
        last_month_end = datetime.date(last_month_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_month_end = datetime.date(last_month_year, last_month + 1, 1) - datetime.timedelta(days=1)
    
    logger.debug(f"Last month date range: {last_month_start} to {last_month_end}")
    
    # Get user's budget settings
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"User not found for ID: {user_id}")
            return {
                "success": False,
                "message": "User not found",
                "data": None
            }
        
        monthly_budget = user.monthly_budget if hasattr(user, 'monthly_budget') else 0
        logger.debug(f"User monthly budget: {monthly_budget}")
    except Exception as e:
        logger.error(f"Error getting user data: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving user data: {str(e)}",
            "data": None
        }
    
    # Get last month's expenses by category
    try:
        sql_query = """
        SELECT category, SUM(amount) as total 
        FROM expenses
        WHERE user_id = :user_id 
            AND date BETWEEN :start_date AND :end_date
        GROUP BY category
        ORDER BY total DESC
        """
        
        params = {
            'user_id': user_id,
            'start_date': last_month_start,
            'end_date': last_month_end
        }
        
        category_totals = db.session.execute(text(sql_query), params).all()
        logger.debug(f"Found {len(category_totals)} categories with expenses")
        
        # If no expenses found for last month, return early with a message
        if not category_totals:
            logger.info(f"No expenses found for last month for user ID: {user_id}")
            return {
                "success": False,
                "message": "No expenses found for last month. Add some expenses to see predictions.",
                "data": None
            }
    except Exception as e:
        logger.error(f"Error executing SQL query: {str(e)}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "data": None
        }
    
    # Get custom budget categories if they exist
    custom_budgets = {}
    try:
        # Check if CustomBudgetCategory exists
        if 'CustomBudgetCategory' in globals():
            budget_categories = CustomBudgetCategory.query.filter_by(user_id=user_id).all()
            for category in budget_categories:
                custom_budgets[category.category_name] = category.monthly_limit
            logger.debug(f"Found {len(custom_budgets)} custom budget categories")
        else:
            logger.warning("CustomBudgetCategory model not found, skipping custom budget lookup")
    except Exception as e:
        logger.error(f"Error fetching custom budgets: {str(e)}")
    
    # Analyze last month's expenses
    categories = []
    total_spent = 0
    potential_alerts = []
    
    for entry in category_totals:
        category_name = entry.category
        category_total = float(entry.total)
        total_spent += category_total
        
        # Check if category has a budget limit
        budget_limit = custom_budgets.get(category_name, 0)
        
        # Calculate projected spending for current month based on last month
        # Using a simple projection (this could be enhanced with more sophisticated prediction)
        projected_spending = category_total * 1.05  # 5% increase projection
        
        # Check if category might exceed budget
        budget_alert = None
        if budget_limit > 0 and projected_spending > budget_limit:
            exceeds_by = projected_spending - budget_limit
            exceeds_by_percent = (exceeds_by / budget_limit) * 100
            budget_alert = {
                "message": f"Projected to exceed budget by ${exceeds_by:.2f} ({exceeds_by_percent:.1f}%)",
                "severity": "high" if exceeds_by_percent > 20 else "medium"
            }
            
            # Add to overall alerts if significant
            if exceeds_by_percent > 15:
                potential_alerts.append({
                    "category": category_name,
                    "projected": projected_spending,
                    "budget": budget_limit,
                    "exceeds_by": exceeds_by,
                    "exceeds_by_percent": exceeds_by_percent
                })
        
        categories.append({
            "name": category_name,
            "last_month_total": category_total,
            "projected": projected_spending,
            "budget_limit": budget_limit,
            "budget_alert": budget_alert
        })
    
    # Overall budget analysis
    overall_budget_status = "good"
    budget_message = "Your spending is within your overall budget."
    
    if monthly_budget > 0:
        projected_total = total_spent * 1.05  # Simple 5% increase projection
        budget_percent = (projected_total / monthly_budget) * 100
        
        if budget_percent > 95:
            overall_budget_status = "warning"
            budget_message = f"Your projected spending is at {budget_percent:.1f}% of your monthly budget."
        
        if budget_percent > 100:
            overall_budget_status = "danger"
            budget_message = f"Your projected spending exceeds your monthly budget by ${(projected_total - monthly_budget):.2f}."
    
    # Generate savings suggestions based on potential alerts
    savings_suggestions = []
    if potential_alerts:
        for alert in potential_alerts:
            suggestion = {
                "category": alert["category"],
                "message": f"Consider reducing spending in {alert['category']} by ${alert['exceeds_by']:.2f} to stay within budget."
            }
            savings_suggestions.append(suggestion)
    
    return {
        "success": True,
        "message": "Predictions generated successfully",
        "data": {
            "month_analyzed": last_month_start.strftime("%B %Y"),
            "current_month": today.strftime("%B %Y"),
            "total_spent_last_month": total_spent,
            "monthly_budget": monthly_budget,
            "projected_total": total_spent * 1.05,
            "overall_budget_status": overall_budget_status,
            "budget_message": budget_message,
            "categories": categories,
            "savings_suggestions": savings_suggestions
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
    logger.debug(f"Generating expense forecast for user ID: {user_id}")
    
    # Get historical expense data by month
    try:
        if category:
            sql_query = """
            SELECT 
                EXTRACT(YEAR FROM date) as year,
                EXTRACT(MONTH FROM date) as month,
                SUM(amount) as total
            FROM expenses
            WHERE user_id = :user_id AND category = :category
            GROUP BY year, month
            ORDER BY year, month
            """
            params = {'user_id': user_id, 'category': category}
        else:
            sql_query = """
            SELECT 
                EXTRACT(YEAR FROM date) as year,
                EXTRACT(MONTH FROM date) as month,
                SUM(amount) as total
            FROM expenses
            WHERE user_id = :user_id
            GROUP BY year, month
            ORDER BY year, month
            """
            params = {'user_id': user_id}
        
        monthly_expenses = db.session.execute(text(sql_query), params).all()
        
        if not monthly_expenses:
            return {
                'success': False,
                'message': 'Not enough historical expense data to generate forecast',
                'data': None
            }
        
        # Convert result to usable format
        historical_data = []
        for entry in monthly_expenses:
            month_date = datetime.date(int(entry.year), int(entry.month), 1)
            historical_data.append({
                'date': month_date.strftime('%Y-%m'),
                'expense': float(entry.total),
                'month_name': month_date.strftime('%b %Y')
            })
        
        # Calculate moving average for forecast
        moving_avg_period = min(3, len(historical_data))  # Use up to last 3 months for moving average
        
        if len(historical_data) >= moving_avg_period:
            recent_total = sum(item['expense'] for item in historical_data[-moving_avg_period:])
            baseline = recent_total / moving_avg_period
        else:
            baseline = historical_data[-1]['expense'] if historical_data else 0
        
        # Generate forecast for next 'months_ahead' months
        forecast_data = []
        current_date = datetime.date.today()
        
        # Start from next month
        if current_date.month == 12:
            forecast_month = 1
            forecast_year = current_date.year + 1
        else:
            forecast_month = current_date.month + 1
            forecast_year = current_date.year
        
        for i in range(months_ahead):
            # Apply a small random adjustment to make the forecast look natural
            # In a real application, you might use more advanced techniques like ARIMA
            # or add seasonal factors
            adjustment = 1.0 + ((i + 1) * 0.03)  # 3% increase per month projection
            
            forecast_date = datetime.date(forecast_year, forecast_month, 1)
            forecast_amount = baseline * adjustment
            
            forecast_data.append({
                'date': forecast_date.strftime('%Y-%m'),
                'expense': round(forecast_amount, 2),
                'month_name': forecast_date.strftime('%b %Y')
            })
            
            # Move to next month
            if forecast_month == 12:
                forecast_month = 1
                forecast_year += 1
            else:
                forecast_month += 1
        
        # Get user's budget details if available
        monthly_budget = 0
        category_budget = 0
        
        try:
            user = User.query.get(user_id)
            if user and hasattr(user, 'monthly_budget'):
                monthly_budget = user.monthly_budget
            
            if category and 'CustomBudgetCategory' in globals():
                custom_budget = CustomBudgetCategory.query.filter_by(
                    user_id=user_id,
                    category_name=category
                ).first()
                
                if custom_budget:
                    category_budget = custom_budget.monthly_limit
        except Exception as e:
            logger.warning(f"Could not fetch budget information: {str(e)}")
        
        # Combine historical and forecast data
        all_data = historical_data + forecast_data
        
        # Get budget lines for chart
        budget_lines = []
        if category and category_budget > 0:
            budget_lines.append({
                'name': f'{category} Budget',
                'value': category_budget
            })
        elif not category and monthly_budget > 0:
            budget_lines.append({
                'name': 'Monthly Budget',
                'value': monthly_budget
            })
        
        return {
            'success': True,
            'message': 'Forecast generated successfully',
            'data': {
                'all_data': all_data,
                'historical_data': historical_data,
                'forecast_data': forecast_data,
                'budget_lines': budget_lines,
                'category': category
            }
        }
    
    except Exception as e:
        logger.error(f"Error generating expense forecast: {str(e)}")
        return {
            'success': False,
            'message': f'Error generating forecast: {str(e)}',
            'data': None
        }