"""
Visualization module for the Expense Tracker application.
Generates chart data for visualizing expense patterns.
"""

import json
import datetime
import calendar
from typing import List, Dict, Any, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Custom JSON encoder to handle NumPy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, datetime.date):
            return o.isoformat()
        return super(NumpyEncoder, self).default(o)

def generate_category_distribution_chart(expenses: List[Any]) -> str:
    """
    Generate a pie chart showing the distribution of expenses by category.
    
    Args:
        expenses: List of Expense objects
        
    Returns:
        JSON string representation of the chart data
    """
    if not expenses:
        return json.dumps({
            "data": [],
            "layout": {"title": "No data available"}
        }, cls=NumpyEncoder)
    
    # Create a dataframe from expenses
    df = pd.DataFrame([
        {"category": expense.category, "amount": expense.amount}
        for expense in expenses
    ])
    
    # Group by category and sum amounts
    category_totals = df.groupby("category").sum().reset_index()
    
    # Create a pie chart
    fig = px.pie(
        category_totals, 
        values="amount", 
        names="category",
        title="Expense Distribution by Category",
        hole=0.4,  # Create a donut chart
        color_discrete_sequence=px.colors.sequential.Plasma
    )
    
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=40, b=80, l=40, r=40)
    )
    
    return json.dumps(fig.to_dict(), cls=NumpyEncoder)

def generate_monthly_trend_chart(
    monthly_data: List[Dict[str, Any]]
) -> str:
    """
    Generate a line chart showing the monthly expense trends.
    
    Args:
        monthly_data: List of monthly summary dictionaries
        
    Returns:
        JSON string representation of the chart data
    """
    if not monthly_data:
        return json.dumps({
            "data": [],
            "layout": {"title": "No data available"}
        }, cls=NumpyEncoder)
    
    # Create a dataframe from monthly data
    df = pd.DataFrame(monthly_data)
    
    # Create date labels
    df["month_year"] = df.apply(
        lambda x: f"{x['month']} {x['year']}", axis=1
    )
    
    # Sort by year and month
    # Use a dictionary for month name to number mapping to avoid indexing issues
    month_to_num = {month: i for i, month in enumerate(calendar.month_name) if month}
    df["sort_key"] = df.apply(
        lambda x: x["year"] * 100 + month_to_num.get(x["month"], 0), axis=1
    )
    df = df.sort_values("sort_key")
    
    # Create a line chart
    fig = px.line(
        df, 
        x="month_year", 
        y="total_amount",
        markers=True,
        title="Monthly Expense Trend",
        labels={"month_year": "Month", "total_amount": "Total Expenses ($)"},
        color_discrete_sequence=["#6200ee"]
    )
    
    fig.update_layout(
        xaxis=dict(tickangle=45),
        margin=dict(t=40, b=80, l=60, r=40)
    )
    
    return json.dumps(fig.to_dict(), cls=NumpyEncoder)

def generate_daily_expense_chart(expenses: List[Any], days: int = 30) -> str:
    """
    Generate a bar chart showing daily expenses for the past X days.
    
    Args:
        expenses: List of Expense objects
        days: Number of days to include in the chart
        
    Returns:
        JSON string representation of the chart data
    """
    if not expenses:
        return json.dumps({
            "data": [],
            "layout": {"title": "No data available"}
        }, cls=NumpyEncoder)
    
    # Get date range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days-1)
    
    # Create a dataframe from expenses
    df = pd.DataFrame([
        {"date": expense.date, "amount": expense.amount}
        for expense in expenses
        if hasattr(expense, "date") and expense.date >= start_date and expense.date <= end_date
    ])
    
    if df.empty:
        return json.dumps({
            "data": [],
            "layout": {"title": f"No data available for the past {days} days"}
        }, cls=NumpyEncoder)
    
    # Group by date and sum amounts
    daily_totals = df.groupby("date").sum().reset_index()
    
    # Create a bar chart
    fig = px.bar(
        daily_totals, 
        x="date", 
        y="amount",
        title=f"Daily Expenses (Past {days} Days)",
        labels={"date": "Date", "amount": "Total Expenses ($)"},
        color_discrete_sequence=["#03dac6"]
    )
    
    fig.update_layout(
        xaxis=dict(tickangle=45),
        margin=dict(t=40, b=80, l=60, r=40)
    )
    
    return json.dumps(fig.to_dict(), cls=NumpyEncoder)

def generate_weekly_expenses_chart(expenses: List[Any], weeks: int = 4) -> str:
    """
    Generate a stacked bar chart showing weekly expenses by category.
    
    Args:
        expenses: List of Expense objects
        weeks: Number of weeks to include in the chart
        
    Returns:
        JSON string representation of the chart data
    """
    if not expenses:
        return json.dumps({
            "data": [],
            "layout": {"title": "No data available"}
        }, cls=NumpyEncoder)
    
    # Get date range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=weeks*7)
    
    # Create a dataframe from expenses
    df = pd.DataFrame([
        {"date": expense.date, "amount": expense.amount, "category": expense.category}
        for expense in expenses
        if hasattr(expense, "date") and expense.date >= start_date and expense.date <= end_date
    ])
    
    if df.empty:
        return json.dumps({
            "data": [],
            "layout": {"title": f"No data available for the past {weeks} weeks"}
        }, cls=NumpyEncoder)
    
    # Add week number
    df['week'] = df['date'].apply(lambda x: f"Week {(x - start_date).days // 7 + 1}")
    
    # Group by week and category, sum amounts
    weekly_category_totals = df.groupby(['week', 'category']).sum().reset_index()
    
    # Calculate the average weekly expense for all categories combined
    total_by_week = df.groupby('week')['amount'].sum().reset_index()
    avg_weekly_expense = total_by_week['amount'].mean()
    
    # Sort by week to ensure proper order
    weeks_order = [f"Week {i+1}" for i in range(weeks)]
    weekly_category_totals['week'] = pd.Categorical(
        weekly_category_totals['week'], 
        categories=weeks_order, 
        ordered=True
    )
    weekly_category_totals = weekly_category_totals.sort_values('week')
    
    # Get unique categories
    categories = weekly_category_totals['category'].unique()
    
    # Create a stacked bar chart
    fig = go.Figure()
    
    # Define a color palette for categories
    colors = px.colors.qualitative.Bold
    
    # Add traces for each category
    for i, category in enumerate(categories):
        category_data = weekly_category_totals[weekly_category_totals['category'] == category]
        fig.add_trace(go.Bar(
            x=category_data['week'],
            y=category_data['amount'],
            name=category,
            marker_color=colors[i % len(colors)]
        ))
    
    # Update the layout
    fig.update_layout(
        barmode='stack',
        title="Expenses by Week",
        xaxis=dict(title=''),
        yaxis=dict(
            title='Amount ($)',
            range=[0, total_by_week['amount'].max() * 1.1]  # Set max y slightly higher than data
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    # Create a custom annotation for average weekly expense
    fig.add_annotation(
        text=f"Average Weekly Expense: ${avg_weekly_expense:.2f}",
        xref="paper", yref="paper",
        x=0.5, y=-0.15,
        showarrow=False,
        font=dict(size=14)
    )
    
    return json.dumps({
        "data": fig.to_dict()["data"],
        "layout": fig.to_dict()["layout"],
        "avg_weekly_expense": float(avg_weekly_expense)
    }, cls=NumpyEncoder)

def generate_income_vs_expenses_chart(
    expenses: List[Any], 
    income: float = 4000,
    period: int = 30
) -> str:
    """
    Generate a donut chart showing income vs expenses and savings.
    
    Args:
        expenses: List of Expense objects
        income: Monthly income amount (default: 4000)
        period: Number of days to calculate expenses (default: 30)
        
    Returns:
        JSON string representation of the chart data
    """
    if not expenses:
        return json.dumps({
            "data": [],
            "layout": {"title": "No data available"}
        }, cls=NumpyEncoder)
    
    # Get date range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=period-1)
    
    # Calculate total expenses for the period
    total_expenses = sum(
        expense.amount for expense in expenses
        if hasattr(expense, "date") and start_date <= expense.date <= end_date
    )
    
    # Calculate savings
    savings = income - total_expenses
    savings_percent = (savings / income) * 100 if income > 0 else 0
    expense_percent = (total_expenses / income) * 100 if income > 0 else 0
    
    # Create data for the chart
    labels = ['Expenses', 'Savings']
    values = [total_expenses, savings]
    colors = ['#FF5252', '#00C853']  # Red for expenses, green for savings
    
    # Create a donut chart
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.6,
        marker=dict(colors=colors),
        textinfo='label+percent',
        insidetextorientation='radial'
    )])
    
    # Update layout
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f'<b>{savings_percent:.0f}%</b><br>Savings',
            x=0.5, y=0.5,
            font_size=16,
            showarrow=False
        )],
        margin=dict(t=30, b=30, l=30, r=30)
    )
    
    return json.dumps({
        "data": fig.to_dict()["data"],
        "layout": fig.to_dict()["layout"],
        "total_expenses": float(total_expenses),
        "income": float(income),
        "savings": float(savings),
        "expense_percent": float(expense_percent),
        "savings_percent": float(savings_percent)
    }, cls=NumpyEncoder)

def generate_category_comparison_chart(
    expenses: List[Any],
    period1: Tuple[datetime.date, datetime.date],
    period2: Tuple[datetime.date, datetime.date],
    period1_name: str = "Current Month",
    period2_name: str = "Previous Month"
) -> str:
    """
    Generate a comparison bar chart of category expenses between two periods.
    
    Args:
        expenses: List of Expense objects
        period1: Tuple of (start_date, end_date) for the first period
        period2: Tuple of (start_date, end_date) for the second period
        period1_name: Name of the first period
        period2_name: Name of the second period
        
    Returns:
        JSON string representation of the chart data
    """
    if not expenses:
        return json.dumps({
            "data": [],
            "layout": {"title": "No data available"}
        }, cls=NumpyEncoder)
    
    # Create dataframes for the two periods
    period1_expenses = [
        {"category": expense.category, "amount": expense.amount, "period": period1_name}
        for expense in expenses
        if hasattr(expense, "date") and period1[0] <= expense.date <= period1[1]
    ]
    
    period2_expenses = [
        {"category": expense.category, "amount": expense.amount, "period": period2_name}
        for expense in expenses
        if hasattr(expense, "date") and period2[0] <= expense.date <= period2[1]
    ]
    
    df = pd.DataFrame(period1_expenses + period2_expenses)
    
    if df.empty:
        return json.dumps({
            "data": [],
            "layout": {"title": "No data available for the specified periods"}
        }, cls=NumpyEncoder)
    
    # Group by category and period, sum amounts
    category_totals = df.groupby(["category", "period"]).sum().reset_index()
    
    # Create a grouped bar chart
    fig = px.bar(
        category_totals, 
        x="category", 
        y="amount",
        color="period",
        barmode="group",
        title=f"Category Comparison: {period1_name} vs {period2_name}",
        labels={"category": "Category", "amount": "Total Expenses ($)", "period": "Period"},
        color_discrete_sequence=["#6200ee", "#03dac6"]
    )
    
    fig.update_layout(
        xaxis=dict(tickangle=45),
        margin=dict(t=40, b=100, l=60, r=40),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )
    
    return json.dumps(fig.to_dict(), cls=NumpyEncoder)