from flask import render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta
import logging
import json
import calendar
from app import app, db
from models import Expense
import plaid_service
import visualization

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Homepage with expense list and form"""
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = db.session.query(Expense.category).distinct().order_by(Expense.category).all()
    category_list = [cat[0] for cat in categories]
    today_date = datetime.today().strftime('%Y-%m-%d')
    return render_template('index.html', expenses=expenses, categories=category_list, today_date=today_date)

@app.route('/add_expense', methods=['POST'])
def add_expense():
    """Add a new expense"""
    try:
        date_str = request.form.get('date')
        if date_str == 'today':
            date = datetime.today().date()
        else:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        amount = float(request.form.get('amount', 0))
        
        # Validate input
        if not description:
            flash('Description cannot be empty', 'danger')
            return redirect(url_for('index'))
        
        if not category:
            flash('Category cannot be empty', 'danger')
            return redirect(url_for('index'))
        
        if amount <= 0:
            flash('Amount must be greater than 0', 'danger')
            return redirect(url_for('index'))
        
        # Create and save expense
        expense = Expense(
            date=date,
            description=description,
            category=category,
            amount=amount
        )
        
        db.session.add(expense)
        db.session.commit()
        
        flash('Expense added successfully!', 'success')
    except Exception as e:
        logger.exception("Error adding expense")
        flash(f'Error adding expense: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('index'))

@app.route('/expenses/category/<category>')
def expenses_by_category(category):
    """Show expenses filtered by category"""
    expenses = Expense.query.filter_by(category=category).order_by(Expense.date.desc()).all()
    categories = db.session.query(Expense.category).distinct().order_by(Expense.category).all()
    category_list = [cat[0] for cat in categories]
    today_date = datetime.today().strftime('%Y-%m-%d')
    return render_template('index.html', 
                          expenses=expenses, 
                          categories=category_list, 
                          selected_category=category,
                          today_date=today_date)

@app.route('/summary')
def monthly_summary():
    """Show monthly expense summary"""
    # SQL query for monthly summary using SQLAlchemy
    monthly_data = db.session.query(
        db.func.extract('month', Expense.date).label('month'),
        db.func.extract('year', Expense.date).label('year'),
        db.func.sum(Expense.amount).label('total_amount')
    ).group_by(
        db.func.extract('year', Expense.date),
        db.func.extract('month', Expense.date)
    ).order_by(
        db.func.extract('year', Expense.date).desc(),
        db.func.extract('month', Expense.date).desc()
    ).all()
    
    # Format the data for the template
    summary_data = []
    for month_num, year, total in monthly_data:
        month_name = datetime(int(year), int(month_num), 1).strftime('%B')
        summary_data.append({
            'month': month_name,
            'year': int(year),
            'total_amount': float(total)
        })
    
    return render_template('summary.html', summaries=summary_data)

@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    """Delete an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!', 'success')
    except Exception as e:
        logger.exception("Error deleting expense")
        flash(f'Error deleting expense: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('index'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    """Show expense analytics dashboard with charts"""
    # Get all expenses
    expenses = Expense.query.all()
    
    # Generate chart data
    category_chart_data = visualization.generate_category_distribution_chart(expenses)
    
    # Get monthly summary data
    monthly_data = db.session.query(
        db.func.extract('month', Expense.date).label('month'),
        db.func.extract('year', Expense.date).label('year'),
        db.func.sum(Expense.amount).label('total_amount')
    ).group_by(
        db.func.extract('year', Expense.date),
        db.func.extract('month', Expense.date)
    ).order_by(
        db.func.extract('year', Expense.date).desc(),
        db.func.extract('month', Expense.date).desc()
    ).all()
    
    # Format the data for the monthly chart
    summary_data = []
    for month_num, year, total in monthly_data:
        month_name = datetime(int(year), int(month_num), 1).strftime('%B')
        summary_data.append({
            'month': month_name,
            'year': int(year),
            'total_amount': float(total)
        })
    
    monthly_chart_data = visualization.generate_monthly_trend_chart(summary_data)
    
    # Generate daily expense chart
    daily_chart_data = visualization.generate_daily_expense_chart(expenses)
    
    # Generate category comparison chart (current month vs previous month)
    today = datetime.today()
    first_day_current_month = datetime(today.year, today.month, 1).date()
    last_day_current_month = datetime(
        today.year, 
        today.month, 
        calendar.monthrange(today.year, today.month)[1]
    ).date()
    
    if today.month == 1:
        first_day_prev_month = datetime(today.year - 1, 12, 1).date()
        last_day_prev_month = datetime(today.year - 1, 12, 31).date()
    else:
        first_day_prev_month = datetime(today.year, today.month - 1, 1).date()
        last_day_prev_month = datetime(
            today.year, 
            today.month - 1, 
            calendar.monthrange(today.year, today.month - 1)[1]
        ).date()
    
    current_month_name = first_day_current_month.strftime("%B")
    prev_month_name = first_day_prev_month.strftime("%B")
    
    comparison_chart_data = visualization.generate_category_comparison_chart(
        expenses,
        (first_day_current_month, last_day_current_month),
        (first_day_prev_month, last_day_prev_month),
        f"{current_month_name} {today.year}",
        f"{prev_month_name} {first_day_prev_month.year}"
    )
    
    return render_template(
        'dashboard.html',
        category_chart_data=category_chart_data,
        monthly_chart_data=monthly_chart_data,
        daily_chart_data=daily_chart_data,
        comparison_chart_data=comparison_chart_data
    )

# Plaid integration routes
@app.route('/import')
def import_plaid_data():
    """Show page to import data from Plaid"""
    transactions = None
    transaction_data = None
    use_sample = request.args.get('use_sample', 'false') == 'true'
    
    today_date = datetime.today()
    thirty_days_ago = today_date - timedelta(days=30)
    
    if use_sample:
        # Generate sample transactions
        transactions = plaid_service.generate_mock_transactions(
            thirty_days_ago.date(),
            today_date.date(),
            50
        )
        transaction_data = json.dumps(transactions)
    
    return render_template(
        'plaid_import.html',
        transactions=transactions,
        transaction_data=transaction_data,
        today_date=today_date.date(),
        thirty_days_ago=thirty_days_ago.date()
    )

@app.route('/get_link_token')
def get_link_token():
    """Get a link token from Plaid"""
    link_token_response = plaid_service.create_link_token()
    return jsonify(link_token_response)

@app.route('/exchange_public_token', methods=['POST'])
def exchange_public_token():
    """Exchange a public token for an access token"""
    try:
        request_data = request.get_json()
        public_token = request_data.get('public_token')
        exchange_response = plaid_service.exchange_public_token(public_token)
        return jsonify(exchange_response)
    except Exception as e:
        logger.exception("Error exchanging public token")
        return jsonify({"error": str(e)})

@app.route('/get_plaid_transactions')
def get_plaid_transactions():
    """Get transactions from Plaid"""
    try:
        access_token = request.args.get('access_token')
        
        # Get date range (default to last 30 days)
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=30)
        
        # Get transactions
        transactions = plaid_service.get_transactions(access_token, start_date, end_date)
        transaction_data = json.dumps(transactions)
        
        return render_template(
            'plaid_import.html',
            transactions=transactions,
            transaction_data=transaction_data,
            today_date=end_date,
            thirty_days_ago=start_date
        )
    except Exception as e:
        logger.exception("Error getting Plaid transactions")
        flash(f"Error getting transactions: {str(e)}", "danger")
        return redirect(url_for('import_plaid_data'))

@app.route('/import_sample_data', methods=['POST'])
def import_sample_data():
    """Import sample transaction data"""
    try:
        # Get form data
        num_transactions = int(request.form.get('num_transactions', 50))
        start_date_str = request.form.get('start_date')
        
        # Parse dates
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = (datetime.today() - timedelta(days=30)).date()
        
        end_date = datetime.today().date()
        
        # Generate sample transactions
        transactions = plaid_service.generate_mock_transactions(
            start_date,
            end_date,
            num_transactions
        )
        
        transaction_data = json.dumps(transactions)
        
        return render_template(
            'plaid_import.html',
            transactions=transactions,
            transaction_data=transaction_data,
            today_date=end_date,
            thirty_days_ago=start_date
        )
    except Exception as e:
        logger.exception("Error generating sample data")
        flash(f"Error generating sample data: {str(e)}", "danger")
        return redirect(url_for('import_plaid_data'))

@app.route('/save_imported_data', methods=['POST'])
def save_imported_data():
    """Save imported transaction data to the database"""
    try:
        # Get transaction data from form
        transaction_data = request.form.get('transaction_data')
        
        if not transaction_data:
            flash("No transaction data provided", "danger")
            return redirect(url_for('import_plaid_data'))
        
        # Parse transaction data
        transactions = json.loads(transaction_data)
        
        # Import transactions to database
        count = plaid_service.import_transactions_to_db(transactions, db.session, Expense)
        
        if count > 0:
            flash(f"Successfully imported {count} transactions!", "success")
        else:
            flash("No transactions were imported", "warning")
            
        return redirect(url_for('index'))
    except Exception as e:
        logger.exception("Error saving imported data")
        flash(f"Error saving imported data: {str(e)}", "danger")
        return redirect(url_for('import_plaid_data'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)