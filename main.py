from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, timedelta
from functools import wraps
import logging
import json
import calendar
from app import app, db
from models import User, Expense
from forms import RegistrationForm, LoginForm, ExpenseForm
import plaid_service
import visualization

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login user"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get user's expenses
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    
    # Calculate total amount
    total_amount = sum(expense.amount for expense in expenses)
    
    # Get categories
    categories = db.session.query(Expense.category).filter_by(user_id=current_user.id).distinct().all()
    category_list = [cat[0] for cat in categories]
    
    # Get recent expenses (limit to 5)
    recent_expenses = expenses[:5] if len(expenses) > 5 else expenses
    
    return render_template('profile.html', 
                           title='Profile',
                           expenses=expenses, 
                           recent_expenses=recent_expenses,
                           total_amount=total_amount,
                           categories=category_list)

@app.route('/')
def index():
    """Homepage with expense list and form"""
    form = ExpenseForm()
    form.date.data = datetime.today()
    
    if current_user.is_authenticated:
        # Filter expenses for logged-in user
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        # Get categories for this user
        categories = db.session.query(Expense.category).filter_by(user_id=current_user.id).distinct().order_by(Expense.category).all()
    else:
        # For non-authenticated users, show a simple welcome message instead of expenses
        expenses = []
        # Empty categories for non-authenticated users
        categories = []
    
    category_list = [cat[0] for cat in categories]
    today_date = datetime.today().strftime('%Y-%m-%d')
    return render_template('index.html', expenses=expenses, categories=category_list, today_date=today_date, form=form)

@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    """Add a new expense"""
    form = ExpenseForm()
    
    if form.validate_on_submit():
        try:
            # Create and save expense with user association
            expense = Expense(
                date=form.date.data,
                description=form.description.data,
                category=form.category.data,
                amount=form.amount.data,
                user_id=current_user.id
            )
            
            db.session.add(expense)
            db.session.commit()
            
            flash('Expense added successfully!', 'success')
        except Exception as e:
            logger.exception("Error adding expense")
            flash(f'Error adding expense: {str(e)}', 'danger')
            db.session.rollback()
    else:
        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('index'))

@app.route('/expenses/category/<category>')
def expenses_by_category(category):
    """Show expenses filtered by category"""
    form = ExpenseForm()
    form.date.data = datetime.today()
    
    if current_user.is_authenticated:
        # Filter by category AND user
        expenses = Expense.query.filter_by(category=category, user_id=current_user.id).order_by(Expense.date.desc()).all()
        categories = db.session.query(Expense.category).filter_by(user_id=current_user.id).distinct().order_by(Expense.category).all()
    else:
        # For non-authenticated users, redirect to login
        flash('Please log in to view expenses by category', 'info')
        return redirect(url_for('login'))
        # No need to query expenses or categories as we're redirecting
    
    category_list = [cat[0] for cat in categories]
    today_date = datetime.today().strftime('%Y-%m-%d')
    
    return render_template('index.html',
                          expenses=expenses, 
                          categories=category_list, 
                          selected_category=category,
                          today_date=today_date,
                          form=form)

@app.route('/summary')
@login_required
def monthly_summary():
    """Show monthly expense summary"""
    # SQL query for monthly summary using SQLAlchemy with proper user filtering
    if current_user.is_admin and request.args.get('all_users') == 'true':
        # Admin viewing all users' data
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
    else:
        # Regular user or admin viewing personal data
        monthly_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount')
        ).filter(Expense.user_id == current_user.id).group_by(
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
    
    return render_template('summary.html', summaries=summary_data, is_admin=current_user.is_admin)

@app.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        
        # Check if the user owns this expense or is an admin
        if expense.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to delete this expense.', 'danger')
            return redirect(url_for('index'))
            
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!', 'success')
    except Exception as e:
        logger.exception("Error deleting expense")
        flash(f'Error deleting expense: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('index'))

# Admin check decorator
def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You must be an admin to access this page.', 'danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_view

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    """Show expense analytics dashboard with charts"""
    # Get expenses for the current user
    if current_user.is_admin:
        # Admins can see all expenses or filter by user
        user_id = request.args.get('user_id')
        if user_id:
            expenses = Expense.query.filter_by(user_id=user_id).all()
        else:
            expenses = Expense.query.all()
    else:
        # Regular users can only see their own expenses
        expenses = Expense.query.filter_by(user_id=current_user.id).all()
    
    # Generate chart data
    category_chart_data = visualization.generate_category_distribution_chart(expenses)
    
    # Get monthly summary data for the relevant expenses
    if current_user.is_admin and not request.args.get('user_id'):
        # For admin viewing all expenses
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
    else:
        # For regular users or admin viewing specific user
        user_id = request.args.get('user_id') if current_user.is_admin else current_user.id
        monthly_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount')
        ).filter(Expense.user_id == user_id).group_by(
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
    
    # Get list of users for admin filter
    users = None
    if current_user.is_admin:
        users = User.query.all()
    
    return render_template(
        'dashboard.html',
        category_chart_data=category_chart_data,
        monthly_chart_data=monthly_chart_data,
        daily_chart_data=daily_chart_data,
        comparison_chart_data=comparison_chart_data,
        users=users
    )

# Admin routes
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Admin control panel"""
    users = User.query.all()
    total_expenses = Expense.query.count()
    total_users = User.query.count()
    
    # Get some statistics
    expense_stats = db.session.query(
        db.func.sum(Expense.amount).label('total_amount'),
        db.func.avg(Expense.amount).label('avg_amount'),
        db.func.max(Expense.amount).label('max_amount')
    ).first()
    
    return render_template(
        'admin.html', 
        users=users, 
        total_expenses=total_expenses,
        total_users=total_users,
        expense_stats=expense_stats
    )

@app.route('/admin/make_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def make_admin(user_id):
    """Make a user an admin"""
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash(f'{user.username} is now an admin!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_admin(user_id):
    """Remove admin privileges from a user"""
    if current_user.id == user_id:
        flash('You cannot remove your own admin privileges.', 'danger')
        return redirect(url_for('admin_panel'))
        
    user = User.query.get_or_404(user_id)
    user.is_admin = False
    db.session.commit()
    flash(f'{user.username} is no longer an admin.', 'success')
    return redirect(url_for('admin_panel'))

# Plaid integration routes
@app.route('/import')
@login_required
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
@login_required
def get_link_token():
    """Get a link token from Plaid"""
    link_token_response = plaid_service.create_link_token()
    return jsonify(link_token_response)

@app.route('/exchange_public_token', methods=['POST'])
@login_required
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
@login_required
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
@login_required
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
@login_required
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
        
        # Import transactions to database with user association
        count = plaid_service.import_transactions_to_db(transactions, db.session, Expense, current_user.id)
        
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