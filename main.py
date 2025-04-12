from flask import render_template, request, redirect, url_for, flash, jsonify, session, Response, send_file, make_response, send_from_directory
from markupsafe import Markup
from flask_login import login_user, current_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import datetime, timedelta
from functools import wraps
import logging
import json
import calendar
import csv
import io
import os
import sys
from werkzeug.utils import secure_filename
from app import app, db

# Initialize CSRF protection
csrf = CSRFProtect(app)
from models import (
    User, Expense, UserPreference, Budget, UserNotification, 
    Receipt, CustomBudgetCategory, BusinessUpgradeRequest, ExcelImport
)
from forms import (
    RegistrationForm, LoginForm, ExpenseForm, ReceiptUploadForm, 
    BudgetForm, BusinessUpgradeRequestForm, ExcelImportForm
)
import plaid_service
import visualization
import suggestions
import ai_assistant
import conversation_assistant
import excel_processor
import excel_visualizer
import perplexity_service

# Directory for storing uploaded receipts
UPLOAD_FOLDER = 'static/uploads/receipts'
# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Directory for Excel uploads
EXCEL_UPLOAD_FOLDER = 'uploads/excel'
os.makedirs(EXCEL_UPLOAD_FOLDER, exist_ok=True)

# Directory for templates
TEMPLATES_FOLDER = 'static/templates'
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

# Directory for chart images
TEMP_CHARTS_FOLDER = 'temp_charts'
os.makedirs(TEMP_CHARTS_FOLDER, exist_ok=True)

# Maximum upload file size (5MB)
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Add custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to <br> tags"""
    if not text:
        return ""
    # First replace any existing <br> tags with newlines to avoid duplicates
    text = text.replace('<br>', '\n')
    # Then replace all newlines with <br> tags
    return Markup(text.replace('\n', '<br>'))

@app.template_filter('month_name')
def month_name_filter(month_number):
    """Convert month number to month name"""
    if not month_number:
        return ""
    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    try:
        month_index = int(month_number) - 1
        if 0 <= month_index < 12:
            return month_names[month_index]
        return str(month_number)
    except (ValueError, TypeError):
        return str(month_number)


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
    logger.debug("Login route accessed")
    
    # Additional debugging
    logger.info("===== LOGIN DEBUG =====")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Form data: {request.form}")
    
    if current_user.is_authenticated:
        logger.debug(f"User is already authenticated: {current_user.username}")
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        logger.debug(f"Login form submitted with email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            logger.debug(
                f"User found with email: {form.email.data}, is_admin: {user.is_admin}"
            )
            if user.check_password(form.password.data):
                if user.is_suspended:
                    logger.debug(
                        f"Login attempt for suspended account: {user.username}"
                    )
                    flash(
                        f'This account has been suspended. Reason: {user.suspension_reason or "Not specified"}',
                        'danger')
                    return render_template('login.html',
                                           title='Login',
                                           form=form)

                if not user.is_active:
                    logger.debug(
                        f"Login attempt for inactive account: {user.username}")
                    flash(
                        'This account is inactive. Please contact an administrator.',
                        'danger')
                    return render_template('login.html',
                                           title='Login',
                                           form=form)

                logger.debug("Password check passed, logging in user")
                # Update last login time
                user.last_login = datetime.utcnow()
                db.session.commit()

                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                logger.debug(
                    f"Login successful for user: {user.username}, redirecting to: {next_page or 'index'}"
                )
                return redirect(next_page) if next_page else redirect(
                    url_for('index'))
            else:
                logger.debug("Password check failed")
                flash('Login unsuccessful. Please check email and password.',
                      'danger')
        else:
            logger.debug(f"No user found with email: {form.email.data}")
            flash('Login unsuccessful. Please check email and password.',
                  'danger')
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
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
        Expense.date.desc()).all()

    # Calculate total amount
    total_amount = sum(expense.amount for expense in expenses)

    # Get categories
    categories = db.session.query(
        Expense.category).filter_by(user_id=current_user.id).distinct().all()
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
    
    # Initialize receipt form for the home page
    receipt_form = ReceiptUploadForm()
    
    # Set default date to today for new expense in receipt form
    receipt_form.expense_date.data = datetime.today()

    # Initialize receipts variable
    receipts = []

    if current_user.is_authenticated:
        # Get search, sort, and pagination parameters
        search_query = request.args.get('search', '')
        sort_by = request.args.get('sort_by', 'date')
        sort_order = request.args.get('sort_order', 'desc')
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of expenses per page
        
        # Base query for expenses filtered by current user, excluding Excel imports
        base_query = Expense.query.filter_by(user_id=current_user.id, excel_import_id=None)
        
        # Get all user's expenses for receipt form dropdown selection (including Excel imports for linking purposes)
        user_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        
        # Populate expense dropdown with user's expenses
        if user_expenses:
            receipt_form.expense_id.choices = [(expense.id, f"{expense.date.strftime('%Y-%m-%d')} - {expense.description} (${expense.amount:.2f})") 
                                for expense in user_expenses]
        else:
            # If no expenses, display a placeholder message
            receipt_form.expense_id.choices = [(-1, "No expenses found. Please create a new expense.")]
        
        # Get all user's receipts for display at the bottom of the home page
        if current_user.is_admin and request.args.get('all_users') == 'true':
            receipts = Receipt.query.order_by(Receipt.upload_date.desc()).limit(10).all()
        else:
            receipts = Receipt.query.filter_by(user_id=current_user.id).order_by(Receipt.upload_date.desc()).limit(10).all()
        
        # Apply search filter if provided
        if search_query:
            base_query = base_query.filter(
                db.or_(
                    Expense.description.ilike(f'%{search_query}%'),
                    Expense.category.ilike(f'%{search_query}%')
                )
            )
        
        # Get total count for pagination
        total_items = base_query.count()
        
        # Apply sorting
        if sort_by == 'amount':
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.amount.asc())
            else:
                base_query = base_query.order_by(Expense.amount.desc())
        elif sort_by == 'category':
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.category.asc())
            else:
                base_query = base_query.order_by(Expense.category.desc())
        elif sort_by == 'description':
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.description.asc())
            else:
                base_query = base_query.order_by(Expense.description.desc())
        else:  # default: sort by date
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.date.asc())
            else:
                base_query = base_query.order_by(Expense.date.desc())
        
        # Apply pagination
        paginated_query = base_query.paginate(page=page, per_page=per_page, error_out=False)
        expenses = paginated_query.items
        total_pages = paginated_query.pages
        
        # Get categories for this user
        categories = db.session.query(Expense.category).filter_by(
            user_id=current_user.id).distinct().order_by(
                Expense.category).all()
    else:
        # For non-authenticated users, show a simple welcome message instead of expenses
        expenses = []
        # Empty categories for non-authenticated users
        categories = []
        # Default pagination values for non-authenticated users
        page = 1
        total_items = 0
        total_pages = 0
        search_query = ''
        sort_by = 'date'
        sort_order = 'desc'
        per_page = 10

    category_list = [cat[0] for cat in categories]
    today_date = datetime.today().strftime('%Y-%m-%d')
    return render_template('index.html',
                           expenses=expenses,
                           categories=category_list,
                           today_date=today_date,
                           form=form,
                           # Receipt form and data
                           receipt_form=receipt_form,
                           receipts=receipts if current_user.is_authenticated else [],
                           # Pagination and search variables
                           page=page,
                           total_pages=total_pages,
                           total_items=total_items,
                           search_query=search_query,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           per_page=per_page)


@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    """Add a new expense"""
    form = ExpenseForm()

    if form.validate_on_submit():
        try:
            # Create and save expense with user association
            expense = Expense(date=form.date.data,
                              description=form.description.data,
                              category=form.category.data,
                              amount=form.amount.data,
                              user_id=current_user.id)

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
    
    # Initialize receipt form for the home page
    receipt_form = ReceiptUploadForm()
    
    # Set default date to today for new expense in receipt form
    receipt_form.expense_date.data = datetime.today()

    if current_user.is_authenticated:
        # Get search, sort, and pagination parameters
        search_query = request.args.get('search', '')
        sort_by = request.args.get('sort_by', 'date')
        sort_order = request.args.get('sort_order', 'desc')
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of expenses per page
        
        # Base query filtered by category AND user, excluding Excel imports
        base_query = Expense.query.filter_by(category=category, user_id=current_user.id, excel_import_id=None)
        
        # Get all user's expenses for receipt form dropdown selection
        user_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        
        # Populate expense dropdown with user's expenses
        if user_expenses:
            receipt_form.expense_id.choices = [(expense.id, f"{expense.date.strftime('%Y-%m-%d')} - {expense.description} (${expense.amount:.2f})") 
                                for expense in user_expenses]
        else:
            # If no expenses, display a placeholder message
            receipt_form.expense_id.choices = [(-1, "No expenses found. Please create a new expense.")]
        
        # Get all user's receipts for display at the bottom of the home page
        if current_user.is_admin and request.args.get('all_users') == 'true':
            receipts = Receipt.query.order_by(Receipt.upload_date.desc()).limit(10).all()
        else:
            receipts = Receipt.query.filter_by(user_id=current_user.id).order_by(Receipt.upload_date.desc()).limit(10).all()
        
        # Apply search filter if provided
        if search_query:
            base_query = base_query.filter(
                db.or_(
                    Expense.description.ilike(f'%{search_query}%'),
                    Expense.category.ilike(f'%{search_query}%')
                )
            )
        
        # Get total count for pagination
        total_items = base_query.count()
        
        # Apply sorting
        if sort_by == 'amount':
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.amount.asc())
            else:
                base_query = base_query.order_by(Expense.amount.desc())
        elif sort_by == 'category':
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.category.asc())
            else:
                base_query = base_query.order_by(Expense.category.desc())
        elif sort_by == 'description':
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.description.asc())
            else:
                base_query = base_query.order_by(Expense.description.desc())
        else:  # default: sort by date
            if sort_order == 'asc':
                base_query = base_query.order_by(Expense.date.asc())
            else:
                base_query = base_query.order_by(Expense.date.desc())
        
        # Apply pagination
        paginated_query = base_query.paginate(page=page, per_page=per_page, error_out=False)
        expenses = paginated_query.items
        total_pages = paginated_query.pages
        
        # Get categories for this user
        categories = db.session.query(Expense.category).filter_by(
            user_id=current_user.id).distinct().order_by(
                Expense.category).all()
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
                           form=form,
                           receipt_form=receipt_form,
                           receipts=receipts,
                           # Pagination and search variables
                           page=page,
                           total_pages=total_pages,
                           total_items=total_items,
                           search_query=search_query,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           per_page=per_page)


@app.route('/summary')
@login_required
def monthly_summary():
    """Show monthly expense summary"""
    logger.debug(
        f"Accessing monthly summary route, user: {current_user.username}, admin: {current_user.is_admin}"
    )

    # Add explicit debug for user ID
    user_id = current_user.id
    logger.debug(f"Current user ID: {user_id}")

    # Count all expenses for this user to verify data exists
    expense_count = db.session.query(Expense).filter(
        Expense.user_id == user_id).count()
    logger.debug(f"User {user_id} has {expense_count} total expenses")

    # Show some sample expenses for debugging
    sample_expenses = db.session.query(Expense).filter(
        Expense.user_id == user_id).limit(3).all()
    for expense in sample_expenses:
        logger.debug(
            f"Sample expense: id={expense.id}, date={expense.date}, amount={expense.amount}, user_id={expense.user_id}"
        )

    # SQL query for monthly summary using SQLAlchemy with proper user filtering
    if current_user.is_admin and request.args.get('all_users') == 'true':
        # Admin viewing all users' data
        logger.debug("Admin viewing all users' data")
        monthly_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount')).filter(
                Expense.excel_import_id == None).group_by(
                db.func.extract('year', Expense.date),
                db.func.extract('month', Expense.date)).order_by(
                    db.func.extract('year', Expense.date).desc(),
                    db.func.extract('month', Expense.date).desc()).all()

        # Get expenses grouped by category for each month, excluding Excel imports
        category_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            Expense.category,
            db.func.sum(Expense.amount).label('category_amount')).filter(
                Expense.excel_import_id == None).group_by(
                db.func.extract('year', Expense.date),
                db.func.extract('month', Expense.date),
                Expense.category).order_by(
                    db.func.extract('year', Expense.date).desc(),
                    db.func.extract('month', Expense.date).desc(),
                    db.func.sum(Expense.amount).desc()).all()
    else:
        # Regular user or admin viewing personal data
        logger.debug(f"User viewing personal data: {current_user.id}")
        monthly_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount')).filter(
                Expense.user_id == user_id, 
                Expense.excel_import_id == None).group_by(
                    db.func.extract('year', Expense.date),
                    db.func.extract('month', Expense.date)).order_by(
                        db.func.extract('year', Expense.date).desc(),
                        db.func.extract('month', Expense.date).desc()).all()

        # Get expenses grouped by category for each month, excluding Excel imports
        category_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            Expense.category,
            db.func.sum(Expense.amount).label('category_amount')).filter(
                Expense.user_id == user_id,
                Expense.excel_import_id == None).group_by(
                    db.func.extract('year', Expense.date),
                    db.func.extract('month', Expense.date),
                    Expense.category).order_by(
                        db.func.extract('year', Expense.date).desc(),
                        db.func.extract('month', Expense.date).desc(),
                        db.func.sum(Expense.amount).desc()).all()

    # Format the data for the template
    summary_data = []
    logger.debug(f"Monthly data count: {len(monthly_data)}")

    # Create a dictionary to store category breakdown for each month/year
    category_breakdown = {}

    # Process category data first
    for month_num, year, category, amount in category_data:
        key = f"{int(year)}-{int(month_num)}"
        if key not in category_breakdown:
            category_breakdown[key] = []

        category_breakdown[key].append({
            'category': category,
            'amount': float(amount)
        })

    # Now process the monthly totals and add category data
    for month_num, year, total in monthly_data:
        month_name = datetime(int(year), int(month_num), 1).strftime('%B')
        key = f"{int(year)}-{int(month_num)}"

        month_data = {
            'month': month_name,
            'year': int(year),
            'total_amount': float(total),
            'categories': category_breakdown.get(key, [])
        }

        summary_data.append(month_data)

    logger.debug(f"Processed summary data count: {len(summary_data)}")

    # Get year-to-date total
    today = datetime.today()
    ytd_total = 0

    if current_user.is_admin and request.args.get('all_users') == 'true':
        ytd_total = db.session.query(db.func.sum(Expense.amount)).filter(
            db.extract('year', Expense.date) == today.year,
            Expense.excel_import_id == None).scalar() or 0
    else:
        ytd_total = db.session.query(db.func.sum(Expense.amount)).filter(
            db.extract('year', Expense.date) == today.year, 
            Expense.user_id == current_user.id,
            Expense.excel_import_id == None).scalar() or 0

    return render_template('summary.html',
                           summaries=summary_data,
                           is_admin=current_user.is_admin,
                           ytd_total=float(ytd_total),
                           current_year=today.year)


@app.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)

        # Check if the user owns this expense or is an admin
        if expense.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to delete this expense.',
                  'danger')
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
        logger.debug(f"Admin required check for user: {current_user}")
        if not current_user.is_authenticated:
            logger.debug("User is not authenticated, redirecting to login")
            flash('You must be an admin to access this page.', 'danger')
            return redirect(url_for('login'))
        elif not current_user.is_admin:
            logger.debug(
                f"User {current_user.username} is not an admin (is_admin={current_user.is_admin})"
            )
            flash('You must be an admin to access this page.', 'danger')
            return redirect(url_for('index'))
        logger.debug(f"Admin check passed for user: {current_user.username}")
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
            base_query = Expense.query.filter_by(user_id=user_id, excel_import_id=None)
        else:
            base_query = Expense.query.filter_by(excel_import_id=None)
    else:
        # Regular users can only see their own expenses
        base_query = Expense.query.filter_by(user_id=current_user.id, excel_import_id=None)
    
    # Get the complete list for total calculations and charts - excluding Excel imported expenses
    expenses = base_query.all()
    
    # Initialize receipt form for the dashboard
    receipt_form = ReceiptUploadForm()
    
    # Set default date to today for new expense
    receipt_form.expense_date.data = datetime.today()
    
    # Get all user's expenses for dropdown selection
    user_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    
    # Populate expense dropdown with user's expenses
    if user_expenses:
        receipt_form.expense_id.choices = [(expense.id, f"{expense.date.strftime('%Y-%m-%d')} - {expense.description} (${expense.amount:.2f})") 
                                for expense in user_expenses]
    else:
        # If no expenses, display a placeholder message
        receipt_form.expense_id.choices = [(-1, "No expenses found. Please create a new expense.")]
    
    # Get all user's receipts for dashboard
    if current_user.is_admin and request.args.get('all_users') == 'true':
        receipts = Receipt.query.order_by(Receipt.upload_date.desc()).limit(10).all()
    else:
        receipts = Receipt.query.filter_by(user_id=current_user.id).order_by(Receipt.upload_date.desc()).limit(10).all()

    # Calculate total expenses
    total_expenses = sum(expense.amount for expense in expenses)
    total_count = len(expenses)

    # Get first and last expense dates
    first_date = "No data"
    last_date = "No data"
    current_date = datetime.now().strftime("%b %d, %Y")

    if expenses:
        first_expense = min(expenses, key=lambda x: x.date)
        last_expense = max(expenses, key=lambda x: x.date)
        first_date = first_expense.date.strftime("%b %d, %Y")
        last_date = last_expense.date.strftime("%b %d, %Y")

    # Generate category distribution chart (pie chart)
    category_chart_data = visualization.generate_category_distribution_chart(
        expenses)

    # Get monthly summary data for the relevant expenses
    if current_user.is_admin and not request.args.get('user_id'):
        # For admin viewing all expenses, excluding Excel imports
        monthly_data_query = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount'),
            db.func.count(Expense.id).label('count')).filter(
                Expense.excel_import_id == None).group_by(
                db.func.extract('year', Expense.date),
                db.func.extract('month', Expense.date)).order_by(
                    db.func.extract('year', Expense.date).desc(),
                    db.func.extract('month', Expense.date).desc())
    else:
        # For regular users or admin viewing specific user, excluding Excel imports
        user_id = request.args.get(
            'user_id') if current_user.is_admin else current_user.id
        monthly_data_query = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount'),
            db.func.count(Expense.id).label('count')).filter(
                Expense.user_id == user_id,
                Expense.excel_import_id == None).group_by(
                    db.func.extract('year', Expense.date),
                    db.func.extract('month', Expense.date)).order_by(
                        db.func.extract('year', Expense.date).desc(),
                        db.func.extract('month', Expense.date).desc())

    monthly_data = monthly_data_query.all()

    # Format the data for the monthly chart
    summary_data = []
    for month_num, year, total_amount, count in monthly_data:
        month_name = datetime(int(year), int(month_num), 1).strftime('%b')
        label = f"{month_name} {int(year)}"

        summary_data.append({
            'month': int(month_num),
            'year': int(year),
            'label': label,
            'value': float(total_amount),
            'count': int(count),
            'month_num': int(month_num)
        })

    # For the simplicity required in the new design, build our own data structure
    monthly_chart_data = {
        'data': summary_data,
        'labels': [item['label'] for item in summary_data],
        'values': [item['value'] for item in summary_data],
    }

    # Get list of users for admin filter
    users = None
    if current_user.is_admin:
        users = User.query.all()

    # Generate charts data
    category_chart_data = visualization.generate_category_distribution_chart(
        expenses)
    weekly_expenses_chart_data = visualization.generate_weekly_expenses_chart(
        expenses)
    # Note: We're now using the simple data structure for monthly_chart_data defined above,
    # instead of overwriting it with visualization.generate_monthly_trend_chart()

    # Income vs expenses chart (with a default income for now)
    income_expense_chart_data = visualization.generate_income_vs_expenses_chart(
        expenses)

    # Category comparison chart (comparing current month vs last month)
    today = datetime.now()
    first_day_current_month = datetime(today.year, today.month, 1).date()
    
    # Correctly handle month rollover for calculating last day of month
    if today.month == 12:
        last_day_current_month = datetime(today.year + 1, 1, 1).date() - timedelta(days=1)
    else:
        last_day_current_month = datetime(today.year, today.month + 1, 1).date() - timedelta(days=1)
    
    # Calculate first day of previous month with proper month rollover handling
    if today.month == 1:
        first_day_prev_month = datetime(today.year - 1, 12, 1).date()
    else:
        first_day_prev_month = datetime(today.year, today.month - 1, 1).date()
    
    # Last day of previous month is the day before first day of current month
    last_day_prev_month = first_day_current_month - timedelta(days=1)

    # Filter expenses for current month and previous month
    current_month_expenses = [exp for exp in expenses if exp.date >= first_day_current_month and exp.date <= last_day_current_month]
    previous_month_expenses = [exp for exp in expenses if exp.date >= first_day_prev_month and exp.date <= last_day_prev_month]

    comparison_chart_data = visualization.generate_category_comparison_chart(
        current_month_expenses, previous_month_expenses, "month")

    # Handle search, sorting, and pagination for expenses
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of expenses per page
    
    # Apply search filter if provided
    if search_query:
        filtered_expenses = [exp for exp in expenses if 
                           search_query.lower() in exp.description.lower() or 
                           search_query.lower() in exp.category.lower()]
    else:
        filtered_expenses = expenses
    
    # Apply sorting
    if sort_by == 'amount':
        if sort_order == 'asc':
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.amount)
        else:
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.amount, reverse=True)
    elif sort_by == 'category':
        if sort_order == 'asc':
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.category.lower())
        else:
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.category.lower(), reverse=True)
    elif sort_by == 'description':
        if sort_order == 'asc':
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.description.lower())
        else:
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.description.lower(), reverse=True)
    else:  # default: sort by date
        if sort_order == 'asc':
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.date)
        else:
            sorted_expenses = sorted(filtered_expenses, key=lambda x: x.date, reverse=True)
    
    # Calculate total number of pages
    total_items = len(sorted_expenses)
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division
    
    # Apply pagination
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    paginated_expenses = sorted_expenses[start_idx:end_idx]
    
    # Get all expenses for display (pagination will be applied in template)
    recent_expenses = paginated_expenses
    
    # Create expense stats for the dashboard
    expense_stats = {
        'total_amount': total_expenses,
        'avg_amount': total_expenses / total_count if total_count > 0 else 0,
        'max_amount': max([exp.amount for exp in expenses]) if expenses else 0,
        'total_count': total_count
    }
    
    # Get user's budget data
    user_id_for_budget = request.args.get('user_id') if current_user.is_admin and request.args.get('user_id') else current_user.id
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Get the current month's budget or create a default one if it doesn't exist
    user_budget = Budget.query.filter_by(
        user_id=user_id_for_budget,
        month=current_month,
        year=current_year
    ).first()
    
    if not user_budget:
        user_budget = Budget(
            user_id=user_id_for_budget,
            month=current_month,
            year=current_year
        )
        db.session.add(user_budget)
        db.session.commit()
    
    # Get custom budget categories
    custom_categories = CustomBudgetCategory.query.filter_by(
        budget_id=user_budget.id
    ).all()
    
    # Calculate category spending
    category_spending = {}
    
    # Map common expense categories to budget categories
    category_map = {
        'food': ['groceries', 'restaurant', 'dining', 'food', 'meal', 'breakfast', 'lunch', 'dinner'],
        'transportation': ['gas', 'fuel', 'car', 'transport', 'uber', 'lyft', 'taxi', 'bus', 'train', 'subway', 'transit'],
        'entertainment': ['movie', 'game', 'entertain', 'concert', 'theater', 'theatre', 'netflix', 'subscription', 'streaming'],
        'bills': ['utility', 'utilities', 'electric', 'water', 'internet', 'phone', 'bill', 'insurance', 'rent', 'mortgage'],
        'shopping': ['shop', 'clothing', 'clothes', 'amazon', 'online', 'mall', 'retail', 'electronics'],
        'other': []  # Catch-all for anything not matching above
    }
    
    # Add custom categories to the map
    for custom_cat in custom_categories:
        # Convert the name to lowercase for matching
        category_key = f"custom_{custom_cat.id}"
        category_map[category_key] = [custom_cat.name.lower()]
        # Initialize spending for this custom category
        category_spending[category_key] = 0
    
    # Initialize category totals for standard categories
    for category in category_map.keys():
        if category not in category_spending:
            category_spending[category] = 0
    
    # Calculate spending in each category
    current_month_expenses = [expense for expense in expenses if expense.date.month == current_month and expense.date.year == current_year]
    
    for expense in current_month_expenses:
        # Find which budget category this expense belongs to
        assigned = False
        expense_category = expense.category.lower()
        
        for budget_cat, keywords in category_map.items():
            if any(keyword in expense_category or expense_category in keyword for keyword in keywords):
                category_spending[budget_cat] += expense.amount
                assigned = True
                break
        
        # If not assigned to any specific category, put in "other"
        if not assigned:
            category_spending['other'] += expense.amount
    
    # Calculate percentage of budget used for each category
    budget_usage = {
        'food': {
            'spent': category_spending['food'],
            'budget': user_budget.food,
            'percentage': min(round((category_spending['food'] / user_budget.food * 100) if user_budget.food > 0 else 0), 100),
            'name': 'Food & Dining',
            'icon': 'bi-cup-hot-fill',
            'color': 'success'
        },
        'transportation': {
            'spent': category_spending['transportation'],
            'budget': user_budget.transportation,
            'percentage': min(round((category_spending['transportation'] / user_budget.transportation * 100) if user_budget.transportation > 0 else 0), 100),
            'name': 'Transportation',
            'icon': 'bi-car-front-fill',
            'color': 'info'
        },
        'entertainment': {
            'spent': category_spending['entertainment'],
            'budget': user_budget.entertainment,
            'percentage': min(round((category_spending['entertainment'] / user_budget.entertainment * 100) if user_budget.entertainment > 0 else 0), 100),
            'name': 'Entertainment',
            'icon': 'bi-film',
            'color': 'primary'
        },
        'bills': {
            'spent': category_spending['bills'],
            'budget': user_budget.bills,
            'percentage': min(round((category_spending['bills'] / user_budget.bills * 100) if user_budget.bills > 0 else 0), 100),
            'name': 'Bills & Utilities',
            'icon': 'bi-file-earmark-text',
            'color': 'danger'
        },
        'shopping': {
            'spent': category_spending['shopping'],
            'budget': user_budget.shopping,
            'percentage': min(round((category_spending['shopping'] / user_budget.shopping * 100) if user_budget.shopping > 0 else 0), 100),
            'name': 'Shopping',
            'icon': 'bi-bag-fill',
            'color': 'warning'
        },
        'other': {
            'spent': category_spending['other'],
            'budget': user_budget.other,
            'percentage': min(round((category_spending['other'] / user_budget.other * 100) if user_budget.other > 0 else 0), 100),
            'name': 'Other',
            'icon': 'bi-three-dots',
            'color': 'secondary'
        },
        'total': {
            'spent': total_expenses,
            'budget': user_budget.total_budget,
            'percentage': min(round((total_expenses / user_budget.total_budget * 100) if user_budget.total_budget > 0 else 0), 100),
            'name': 'Total Budget',
            'icon': 'bi-wallet2',
            'color': 'dark'
        }
    }
    
    # Add custom categories to budget usage
    for custom_cat in custom_categories:
        category_key = f"custom_{custom_cat.id}"
        if category_key in category_spending:
            budget_usage[category_key] = {
                'spent': category_spending[category_key],
                'budget': custom_cat.amount,
                'percentage': min(round((category_spending[category_key] / custom_cat.amount * 100) if custom_cat.amount > 0 else 0), 100),
                'name': custom_cat.name,
                'icon': custom_cat.icon if custom_cat.icon else 'bi-tag-fill',
                'color': custom_cat.color if custom_cat.color else 'secondary',
                'custom': True,
                'id': custom_cat.id
            }
    
    # Use the v2 dashboard template with the new layout
    return render_template(
        'dashboard_v2.html',
        total_expenses=total_expenses,
        total_count=total_count,
        users=users,
        expense_stats=expense_stats,
        recent_expenses=recent_expenses,
        category_chart_data=category_chart_data,
        weekly_expenses_chart_data=weekly_expenses_chart_data,
        monthly_chart_data=monthly_chart_data,
        income_expense_chart_data=income_expense_chart_data,
        comparison_chart_data=comparison_chart_data,
        # Budget data
        user_budget=user_budget,
        budget_usage=budget_usage,
        # Pagination variables
        total_items=total_items,
        per_page=per_page,
        current_page=page,
        # Receipt data for integrated uploading functionality
        receipt_form=receipt_form,
        receipts=receipts,
        is_admin=current_user.is_admin,
        time_period=request.args.get('period', 'month'))


# Admin routes
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Admin control panel"""
    users = User.query.all()
    total_expenses = Expense.query.count()
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    suspended_users = User.query.filter_by(is_suspended=True).count()

    # Get some statistics
    expense_stats = db.session.query(
        db.func.sum(Expense.amount).label('total_amount'),
        db.func.avg(Expense.amount).label('avg_amount'),
        db.func.max(Expense.amount).label('max_amount')).first()

    # Get user spending statistics
    user_spending = []
    for user in users:
        total_spent = db.session.query(db.func.sum(
            Expense.amount)).filter(Expense.user_id == user.id).scalar() or 0
        expense_count = Expense.query.filter_by(user_id=user.id).count()
        last_expense_date = db.session.query(db.func.max(
            Expense.date)).filter(Expense.user_id == user.id).scalar()

        user_spending.append({
            'user_id': user.id,
            'username': user.username,
            'total_spent': total_spent,
            'expense_count': expense_count,
            'last_expense_date': last_expense_date
        })

    return render_template('admin.html',
                           users=users,
                           total_expenses=total_expenses,
                           total_users=total_users,
                           active_users=active_users,
                           suspended_users=suspended_users,
                           expense_stats=expense_stats,
                           user_spending=user_spending)


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


@app.route('/admin/deactivate/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    """Deactivate a user account"""
    if current_user.id == user_id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin_panel'))

    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    flash(f'{user.username}\'s account has been deactivated.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/activate/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    """Activate a user account"""
    user = User.query.get_or_404(user_id)
    user.is_active = True
    # If user was suspended, we also unsuspend them
    if user.is_suspended:
        user.is_suspended = False
        user.suspension_reason = None
    db.session.commit()
    flash(f'{user.username}\'s account has been activated.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/suspend/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def suspend_user(user_id):
    """Suspend a user account"""
    if current_user.id == user_id:
        flash('You cannot suspend your own account.', 'danger')
        return redirect(url_for('admin_panel'))

    reason = request.form.get('suspension_reason',
                              'Account suspended by administrator')
    user = User.query.get_or_404(user_id)
    user.is_suspended = True
    user.suspension_reason = reason
    db.session.commit()
    flash(f'{user.username}\'s account has been suspended.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/user_details/<int:user_id>')
@login_required
@admin_required
def user_details(user_id):
    """Show detailed information about a user"""
    user = User.query.get_or_404(user_id)

    # Get user's expenses
    expenses = Expense.query.filter_by(user_id=user.id).order_by(
        Expense.date.desc()).all()

    # Get user's expense statistics
    total_spent = db.session.query(db.func.sum(
        Expense.amount)).filter(Expense.user_id == user.id).scalar() or 0
    expense_count = len(expenses)

    # Get user's categories
    categories = db.session.query(
        Expense.category).filter_by(user_id=user.id).distinct().all()
    category_list = [cat[0] for cat in categories]

    # Get category spending distribution
    category_spending = []
    for category in category_list:
        category_total = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.user_id == user.id, Expense.category
            == category).scalar() or 0

        category_spending.append({
            'category':
            category,
            'total':
            category_total,
            'percentage':
            (category_total / total_spent * 100) if total_spent > 0 else 0
        })

    # Sort categories by spending (highest first)
    category_spending.sort(key=lambda x: x['total'], reverse=True)

    # Get recent activity (last 5 expenses)
    recent_expenses = expenses[:5] if len(expenses) > 5 else expenses

    # Generate monthly spending chart
    monthly_data = db.session.query(
        db.func.extract('month', Expense.date).label('month'),
        db.func.extract('year', Expense.date).label('year'),
        db.func.sum(Expense.amount).label('total_amount')).filter(
            Expense.user_id == user.id).group_by(
                db.func.extract('year', Expense.date),
                db.func.extract('month', Expense.date)).order_by(
                    db.func.extract('year', Expense.date).desc(),
                    db.func.extract('month', Expense.date).desc()).all()

    # Format the data for the template
    monthly_spending = []
    for month_num, year, total in monthly_data:
        month_name = datetime(int(year), int(month_num), 1).strftime('%B')
        monthly_spending.append({
            'month': month_name,
            'year': int(year),
            'total_amount': float(total)
        })

    return render_template('user_details.html',
                           user=user,
                           expenses=expenses,
                           total_spent=total_spent,
                           expense_count=expense_count,
                           category_spending=category_spending,
                           recent_expenses=recent_expenses,
                           monthly_spending=monthly_spending)


# Export functionality
@app.route('/export/expenses')
@login_required
def export_expenses():
    """Export expenses to CSV file"""
    try:
        # Get filter parameters
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')

        # Base query for expenses
        if current_user.is_admin and user_id:
            # Admin user can export a specific user's expenses
            query = Expense.query.filter_by(user_id=user_id)
            filename_prefix = f"user_{user_id}_expenses"
        elif current_user.is_admin and request.args.get('all_users') == 'true':
            # Admin user can export all users' expenses
            query = Expense.query
            filename_prefix = "all_users_expenses"
        else:
            # Regular user (or admin without specific filters) can only export their own expenses
            query = Expense.query.filter_by(user_id=current_user.id)
            filename_prefix = f"my_expenses"

        # Apply additional filters if provided
        if category:
            query = query.filter_by(category=category)
            filename_prefix = f"{category.lower().replace(' ', '_')}_expenses"

        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Expense.date >= start_date)
            except ValueError:
                flash('Invalid start date format. Using all dates.', 'warning')

        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Expense.date <= end_date)
            except ValueError:
                flash('Invalid end date format. Using all dates.', 'warning')

        # Get expenses ordered by date (newest first)
        expenses = query.order_by(Expense.date.desc()).all()

        if not expenses:
            flash('No expenses found to export.', 'warning')
            return redirect(url_for('index'))

        # Create CSV file in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header row - include user information for admin exports
        if current_user.is_admin and (user_id or request.args.get('all_users')
                                      == 'true'):
            writer.writerow(
                ['Date', 'Description', 'Category', 'Amount', 'User'])
        else:
            writer.writerow(['Date', 'Description', 'Category', 'Amount'])

        # Write expense data
        for expense in expenses:
            row_data = [
                expense.date.strftime('%Y-%m-%d'), expense.description,
                expense.category, f"${expense.amount:.2f}"
            ]

            # Include username for admin exports of all users
            if current_user.is_admin and (
                    user_id or request.args.get('all_users') == 'true'):
                username = User.query.filter_by(
                    id=expense.user_id).first().username
                row_data.append(username)

            writer.writerow(row_data)

        # Prepare response
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition':
                f'attachment; filename={filename_prefix}_{timestamp}.csv'
            })
    except Exception as e:
        logger.exception("Error exporting expenses")
        flash(f'Error exporting expenses: {str(e)}', 'danger')
        return redirect(url_for('index'))


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
            thirty_days_ago.date(), today_date.date(), 50)
        transaction_data = json.dumps(transactions)

    return render_template('plaid_import.html',
                           transactions=transactions,
                           transaction_data=transaction_data,
                           today_date=today_date.date(),
                           thirty_days_ago=thirty_days_ago.date())


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
        transactions = plaid_service.get_transactions(access_token, start_date,
                                                      end_date)
        transaction_data = json.dumps(transactions)

        return render_template('plaid_import.html',
                               transactions=transactions,
                               transaction_data=transaction_data,
                               today_date=end_date,
                               thirty_days_ago=start_date)
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
            start_date, end_date, num_transactions)

        transaction_data = json.dumps(transactions)

        return render_template('plaid_import.html',
                               transactions=transactions,
                               transaction_data=transaction_data,
                               today_date=end_date,
                               thirty_days_ago=start_date)
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
        count = plaid_service.import_transactions_to_db(
            transactions, db.session, Expense, current_user.id)

        if count > 0:
            flash(f"Successfully imported {count} transactions!", "success")
        else:
            flash("No transactions were imported", "warning")

        return redirect(url_for('index'))
    except Exception as e:
        logger.exception("Error saving imported data")
        flash(f"Error saving imported data: {str(e)}", "danger")
        return redirect(url_for('import_plaid_data'))


@app.route('/suggestions')
@login_required
def get_suggestions():
    """Show smart financial suggestions based on expense patterns"""
    logger.debug(f"Accessing suggestions route, user: {current_user.username}")

    # Get all expenses for the current user for analysis
    expenses = Expense.query.filter_by(user_id=current_user.id).all()

    # Calculate previous month name and year for display
    today = datetime.today()
    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year

    prev_month_name = datetime(prev_year, prev_month, 1).strftime('%B')

    # Generate suggestions based on spending patterns
    suggestion_data = suggestions.generate_spending_suggestions(
        expenses, current_user.id)

    return render_template('suggestions.html',
                           suggestions=suggestion_data,
                           prev_month_name=prev_month_name,
                           prev_month_year=prev_year)


# AI Assistant Routes
@app.route('/ai/assistant')
@login_required
def ai_assistant_home():
    """Show AI assistant homepage with analysis options"""
    logger.debug(
        f"Accessing AI assistant homepage, user: {current_user.username}")

    # Get analysis options from AI module
    analysis_options = ai_assistant.get_analysis_options()

    # Get expenses for current user
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

    # Calculate basic stats for the data summary panel
    expense_data = []
    if expenses:
        # Format expenses for AI processing
        expense_data = [{
            'date': e.date,
            'description': e.description,
            'category': e.category,
            'amount': e.amount
        } for e in expenses]

    total_amount = sum(e.amount for e in expenses) if expenses else 0
    expense_count = len(expenses)

    # Get unique categories
    categories = {}
    for expense in expenses:
        if expense.category not in categories:
            categories[expense.category] = 0
        categories[expense.category] += expense.amount

    category_count = len(categories)

    # Get top 5 categories by amount
    top_categories = []
    try:
        if categories:
            sorted_categories = sorted(categories.items(),
                                       key=lambda x: x[1],
                                       reverse=True)
            logger.debug(f"Sorted categories: {sorted_categories[:5]}")
            for name, amount in sorted_categories[:5]:
                percentage = (amount / total_amount *
                              100) if total_amount > 0 else 0
                cat_data = {
                    'name': name,
                    'amount': amount,
                    'percentage': percentage
                }
                logger.debug(f"Adding category: {cat_data}")
                top_categories.append(cat_data)
            logger.debug(f"Final top_categories: {top_categories}")
    except Exception as e:
        logger.error(f"Error processing top categories: {str(e)}")
        top_categories = []

    # Get general expense insights if there are expenses
    analysis_results = None
    if expenses:
        analysis_results = ai_assistant.get_expense_insights(expense_data)

    # Set the current analysis type as general insights
    current_analysis = {
        'title': 'Expense Overview',
        'description': 'General insights about your spending patterns.'
    }

    return render_template('ai/assistant.html',
                           analysis_options=analysis_options,
                           current_analysis=current_analysis,
                           analysis_results=analysis_results,
                           expenses=expense_data,
                           total_amount=total_amount,
                           expense_count=expense_count,
                           category_count=category_count,
                           top_categories=top_categories,
                           time_period='all')


@app.route('/ai/analysis')
@login_required
def ai_analysis():
    """Generate AI analysis based on selected option"""
    logger.debug(f"Accessing AI analysis, user: {current_user.username}")

    # Get analysis type from query parameters
    analysis_type = request.args.get('analysis_type', 'expense_trends')
    time_period = request.args.get('time_period', 'all')

    # Get analysis options
    analysis_options = ai_assistant.get_analysis_options()

    # Get current analysis details
    current_analysis = {
        'title': analysis_options[analysis_type]['title'],
        'description': analysis_options[analysis_type]['description']
    } if analysis_type in analysis_options else {
        'title': 'Custom Analysis',
        'description': 'Tailored financial insights based on your data.'
    }

    # Get expenses based on selected time period
    if current_user.is_admin:
        # Admins can see all expenses or filter by user
        user_id = request.args.get('user_id')
        if user_id:
            query = Expense.query.filter_by(user_id=user_id)
        else:
            query = Expense.query
    else:
        # Regular users can only see their own expenses
        query = Expense.query.filter_by(user_id=current_user.id)

    # Apply time period filter
    today = datetime.today()
    if time_period == 'month':
        # This month only
        start_date = datetime(today.year, today.month, 1)
        end_date = datetime(today.year, today.month,
                            calendar.monthrange(today.year, today.month)[1])
        query = query.filter(Expense.date >= start_date, Expense.date
                             <= end_date)
    elif time_period == 'year':
        # This year only
        start_date = datetime(today.year, 1, 1)
        end_date = datetime(today.year, 12, 31)
        query = query.filter(Expense.date >= start_date, Expense.date
                             <= end_date)

    # Get expenses
    expenses = query.order_by(Expense.date.desc()).all()

    # Format expenses for AI processing
    expense_data = [{
        'date': e.date,
        'description': e.description,
        'category': e.category,
        'amount': e.amount
    } for e in expenses]

    # Generate analysis results
    analysis_results = None
    if expenses:
        # Default monthly income (this could be made configurable in user settings)
        monthly_income = 4000.0

        # Generate analysis based on selected type
        analysis_results = ai_assistant.generate_ai_analysis(
            analysis_type, expense_data, income=monthly_income)

    # Calculate basic stats for the data summary panel
    total_amount = sum(e.amount for e in expenses) if expenses else 0
    expense_count = len(expenses)

    # Get unique categories
    categories = {}
    for expense in expenses:
        if expense.category not in categories:
            categories[expense.category] = 0
        categories[expense.category] += expense.amount

    category_count = len(categories)

    # Get top 5 categories by amount
    top_categories = []
    try:
        if categories:
            sorted_categories = sorted(categories.items(),
                                      key=lambda x: x[1],
                                      reverse=True)
            logger.debug(f"AI analysis - Sorted categories: {sorted_categories[:5]}")
            for name, amount in sorted_categories[:5]:
                percentage = (amount / total_amount *
                              100) if total_amount > 0 else 0
                cat_data = {
                    'name': name,
                    'amount': amount,
                    'percentage': percentage
                }
                logger.debug(f"AI analysis - Adding category: {cat_data}")
                top_categories.append(cat_data)
            logger.debug(f"AI analysis - Final top_categories: {top_categories}")
    except Exception as e:
        logger.error(f"AI analysis - Error processing top categories: {str(e)}")
        top_categories = []

    return render_template('ai/assistant.html',
                           analysis_options=analysis_options,
                           current_analysis=current_analysis,
                           analysis_results=analysis_results,
                           analysis_type=analysis_type,
                           expenses=expense_data,
                           total_amount=total_amount,
                           expense_count=expense_count,
                           category_count=category_count,
                           top_categories=top_categories,
                           time_period=time_period)


# User Preferences Routes
@app.route('/preferences')
@login_required
def preferences():
    """User preferences page"""
    # Get user's preferences or create if they don't exist
    user_pref = UserPreference.query.filter_by(user_id=current_user.id).first()
    if not user_pref:
        user_pref = UserPreference(user_id=current_user.id)
        db.session.add(user_pref)
        db.session.commit()
    
    # Get user's budget or create if it doesn't exist
    user_budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=datetime.utcnow().month,
        year=datetime.utcnow().year
    ).first()
    if not user_budget:
        user_budget = Budget(
            user_id=current_user.id,
            month=datetime.utcnow().month,
            year=datetime.utcnow().year
        )
        db.session.add(user_budget)
        db.session.commit()
    
    return render_template('preferences.html', 
                           title='Preferences',
                           user_pref=user_pref,
                           user_budget=user_budget)


@app.route('/budget/edit', methods=['GET', 'POST'])
@login_required
def edit_budget():
    """Edit user's budget settings and custom categories"""
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Get the user's budget for the current month/year or create a new one
    user_budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        year=current_year
    ).first()
    
    if not user_budget:
        # Create a new budget with default values
        user_budget = Budget(
            user_id=current_user.id,
            month=current_month,
            year=current_year
        )
        db.session.add(user_budget)
        db.session.commit()
        flash('Created a new budget for the current month.', 'info')
    
    # Get user's custom budget categories
    custom_categories = CustomBudgetCategory.query.filter_by(
        budget_id=user_budget.id
    ).all()
    
    # Create the form and populate it with the current budget values
    form = BudgetForm(obj=user_budget) if request.method == 'GET' else BudgetForm()
    
    # Handle adding a new custom category
    if request.method == 'POST' and 'add_custom_category' in request.form:
        category_name = form.custom_category_name.data
        category_amount = form.custom_category_amount.data or 0.0
        
        if category_name:
            # Create a new custom category
            new_category = CustomBudgetCategory(
                budget_id=user_budget.id,
                name=category_name,
                amount=category_amount,
                # Default icon and color with Bootstrap icon prefix
                icon='bi-tag-fill',
                color='primary'
            )
            db.session.add(new_category)
            try:
                db.session.commit()
                flash(f'Added new category: {category_name}', 'success')
            except Exception as e:
                db.session.rollback()
                logger.exception("Error adding custom category")
                flash(f'Error adding category: {str(e)}', 'danger')
            
            return redirect(url_for('edit_budget'))
    
    # Handle deleting a custom category
    if request.method == 'POST' and 'delete_custom_category' in request.form:
        category_id = request.form.get('delete_category_id')
        if category_id:
            category = CustomBudgetCategory.query.get(category_id)
            if category and category.budget_id == user_budget.id:  # Security check
                try:
                    db.session.delete(category)
                    db.session.commit()
                    flash(f'Deleted category: {category.name}', 'success')
                except Exception as e:
                    db.session.rollback()
                    logger.exception("Error deleting custom category")
                    flash(f'Error deleting category: {str(e)}', 'danger')
                
                return redirect(url_for('edit_budget'))
    
    # Handle main budget form submission (standard category updates)
    if form.validate_on_submit() and 'add_custom_category' not in request.form and 'delete_custom_category' not in request.form:
        try:
            # Update the budget with form data
            user_budget.total_budget = form.total_budget.data
            user_budget.food = form.food.data
            user_budget.transportation = form.transportation.data
            user_budget.entertainment = form.entertainment.data
            user_budget.bills = form.bills.data
            user_budget.shopping = form.shopping.data
            user_budget.other = form.other.data
            user_budget.updated_at = datetime.utcnow()
            
            # Update custom category amounts
            for category in custom_categories:
                category_field_name = f'custom_category_{category.id}'
                if category_field_name in request.form:
                    try:
                        amount = float(request.form[category_field_name])
                        category.amount = amount
                    except (ValueError, TypeError):
                        # Skip if value can't be converted to float
                        pass
            
            db.session.commit()
            flash('Budget updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            logger.exception("Error updating budget")
            flash(f'Error updating budget: {str(e)}', 'danger')
    
    # For GET requests or if form validation fails
    return render_template('edit_budget.html', 
                          title='Budget Settings',
                          form=form,
                          user_budget=user_budget,
                          custom_categories=custom_categories)


@app.route('/save_preferences', methods=['POST'])
@login_required
def save_preferences():
    """Save user preferences"""
    try:
        data = request.get_json()
        
        # Get or create user preferences
        user_pref = UserPreference.query.filter_by(user_id=current_user.id).first()
        if not user_pref:
            user_pref = UserPreference(user_id=current_user.id)
            db.session.add(user_pref)
        
        # Update theme settings (this can be sent alone from the theme toggle)
        if 'theme' in data:
            user_pref.theme = data.get('theme')
        
        # Only process these fields if they're in the request (from preferences page)
        if 'notifications' in data:
            # Update notification settings
            notifications = data.get('notifications', {})
            user_pref.email_notifications = notifications.get('email', True)
            user_pref.push_notifications = notifications.get('push', True)
            user_pref.weekly_reports = notifications.get('weeklyReports', True)
            user_pref.monthly_reports = notifications.get('monthlyReports', True)
        
        if 'alerts' in data:
            # Update alert settings
            alerts = data.get('alerts', {})
            user_pref.alerts_enabled = alerts.get('enabled', True)
            user_pref.alert_large_transactions = alerts.get('largeTransactions', True)
            user_pref.alert_low_balance = alerts.get('lowBalance', True)
            user_pref.alert_upcoming_bills = alerts.get('upcomingBills', True)
            user_pref.alert_saving_goal_progress = alerts.get('savingGoalProgress', True)
            user_pref.alert_budget_exceeded = alerts.get('budgetLimitExceeded', True)
        
        # Only update budget settings if provided in the request
        if 'budgets' in data:
            budgets = data.get('budgets', {})
            
            # Get current month's budget or create new one
            user_budget = Budget.query.filter_by(
                user_id=current_user.id,
                month=datetime.utcnow().month,
                year=datetime.utcnow().year
            ).first()
            if not user_budget:
                user_budget = Budget(
                    user_id=current_user.id,
                    month=datetime.utcnow().month,
                    year=datetime.utcnow().year
                )
                db.session.add(user_budget)
            
            # Update budget values
            user_budget.total_budget = float(budgets.get('totalMonthly', 3000))
            user_budget.food = float(budgets.get('food', 500))
            user_budget.transportation = float(budgets.get('transportation', 300))
            user_budget.entertainment = float(budgets.get('entertainment', 200))
            user_budget.bills = float(budgets.get('bills', 800))
            user_budget.shopping = float(budgets.get('shopping', 400))
            user_budget.other = float(budgets.get('other', 800))
        
        db.session.commit()
        
        # Check if any budgets are exceeded and create notifications
        check_budget_limits(current_user.id)
        
        # Set a cookie for theme to ensure persistence between pages
        resp = make_response(jsonify({'success': True}))
        if 'theme' in data or user_pref.theme:
            theme = data.get('theme', user_pref.theme)
            resp.set_cookie('theme', theme, max_age=31536000)  # 1 year
        return resp
    except Exception as e:
        logger.exception("Error saving preferences")
        return jsonify({'success': False, 'error': str(e)})


def check_budget_limits(user_id):
    """Check if user has exceeded any budget limits and create notifications"""
    try:
        # Get current month's budget
        current_month = datetime.utcnow().month
        current_year = datetime.utcnow().year
        user_budget = Budget.query.filter_by(
            user_id=user_id,
            month=current_month,
            year=current_year
        ).first()
        
        if not user_budget:
            return
        
        # Get user's preferences to check if alerts are enabled
        user_pref = UserPreference.query.filter_by(user_id=user_id).first()
        if not user_pref or not user_pref.alerts_enabled or not user_pref.alert_budget_exceeded:
            return
        
        # Get all expenses for the current month
        start_date = datetime(current_year, current_month, 1)
        if current_month == 12:
            end_date = datetime(current_year + 1, 1, 1)
        else:
            end_date = datetime(current_year, current_month + 1, 1)
        
        expenses = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date < end_date
        ).all()
        
        # Calculate totals by category
        category_totals = {}
        for expense in expenses:
            category_totals[expense.category] = category_totals.get(expense.category, 0) + expense.amount
        
        # Check for exceeded budgets
        total_spent = sum(expense.amount for expense in expenses)
        
        # Check total budget
        if total_spent > user_budget.total_budget:
            create_budget_notification(
                user_id, 
                'Total Budget Exceeded', 
                f'You have spent ${total_spent:.2f} out of your ${user_budget.total_budget:.2f} monthly budget.'
            )
        
        # Check category budgets - we'll map common categories to our budget fields
        category_map = {
            'food': ['Food', 'Dining', 'Groceries', 'Restaurant'],
            'transportation': ['Transportation', 'Gas', 'Fuel', 'Car', 'Bus', 'Train', 'Taxi', 'Uber', 'Lyft'],
            'entertainment': ['Entertainment', 'Movies', 'Music', 'Games', 'Events', 'Concert'],
            'bills': ['Bills', 'Utilities', 'Rent', 'Mortgage', 'Electricity', 'Water', 'Internet', 'Phone'],
            'shopping': ['Shopping', 'Clothes', 'Electronics', 'Amazon']
        }
        
        # Calculate category totals based on our mapping
        mapped_totals = {
            'food': 0,
            'transportation': 0,
            'entertainment': 0,
            'bills': 0,
            'shopping': 0,
            'other': 0
        }
        
        for expense in expenses:
            category = expense.category
            mapped = False
            
            for budget_cat, keywords in category_map.items():
                if any(keyword.lower() in category.lower() for keyword in keywords):
                    mapped_totals[budget_cat] += expense.amount
                    mapped = True
                    break
            
            if not mapped:
                mapped_totals['other'] += expense.amount
        
        # Check if any category budgets are exceeded
        if mapped_totals['food'] > user_budget.food:
            create_budget_notification(
                user_id,
                'Food Budget Exceeded',
                f'You have spent ${mapped_totals["food"]:.2f} out of your ${user_budget.food:.2f} food budget this month.'
            )
        
        if mapped_totals['transportation'] > user_budget.transportation:
            create_budget_notification(
                user_id,
                'Transportation Budget Exceeded',
                f'You have spent ${mapped_totals["transportation"]:.2f} out of your ${user_budget.transportation:.2f} transportation budget this month.'
            )
        
        if mapped_totals['entertainment'] > user_budget.entertainment:
            create_budget_notification(
                user_id,
                'Entertainment Budget Exceeded',
                f'You have spent ${mapped_totals["entertainment"]:.2f} out of your ${user_budget.entertainment:.2f} entertainment budget this month.'
            )
        
        if mapped_totals['bills'] > user_budget.bills:
            create_budget_notification(
                user_id,
                'Bills Budget Exceeded',
                f'You have spent ${mapped_totals["bills"]:.2f} out of your ${user_budget.bills:.2f} bills budget this month.'
            )
        
        if mapped_totals['shopping'] > user_budget.shopping:
            create_budget_notification(
                user_id,
                'Shopping Budget Exceeded',
                f'You have spent ${mapped_totals["shopping"]:.2f} out of your ${user_budget.shopping:.2f} shopping budget this month.'
            )
        
        if mapped_totals['other'] > user_budget.other:
            create_budget_notification(
                user_id,
                'Other Budget Exceeded',
                f'You have spent ${mapped_totals["other"]:.2f} out of your ${user_budget.other:.2f} budget for other expenses this month.'
            )
    
    except Exception as e:
        logger.exception(f"Error checking budget limits for user {user_id}: {str(e)}")


def create_budget_notification(user_id, title, message):
    """Create a budget notification for the user"""
    # Check if a similar notification already exists from today
    today = datetime.utcnow().date()
    existing = UserNotification.query.filter(
        UserNotification.user_id == user_id,
        UserNotification.title == title,
        db.func.date(UserNotification.created_at) == today
    ).first()
    
    if not existing:
        notification = UserNotification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type='warning'
        )
        db.session.add(notification)
        db.session.commit()


@app.route('/notifications')
@login_required
def notifications():
    """API endpoint for user notifications"""
    # Get unread notifications
    unread = UserNotification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(UserNotification.created_at.desc()).all()
    
    # Get read notifications (limit to 20)
    read = UserNotification.query.filter_by(
        user_id=current_user.id,
        is_read=True
    ).order_by(UserNotification.created_at.desc()).limit(20).all()
    
    return jsonify({
        'unread': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for n in unread
        ],
        'read': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for n in read
        ]
    })


@app.route('/all-notifications')
@login_required
def all_notifications_page():
    """Page to view all notifications"""
    return render_template('notifications.html', title='Notifications')


@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    notification = UserNotification.query.get_or_404(notification_id)
    
    # Make sure the user owns this notification
    if notification.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})


# Receipt Upload and Management Routes
@app.route('/receipts', methods=['GET'])
@login_required
def receipts():
    """View all receipts and upload form"""
    form = ReceiptUploadForm()
    
    # Set default date to today for new expense
    form.expense_date.data = datetime.today()
    
    # Get all user's expenses for dropdown selection
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    
    # Populate expense dropdown with user's expenses
    if expenses:
        form.expense_id.choices = [(expense.id, f"{expense.date.strftime('%Y-%m-%d')} - {expense.description} (${expense.amount:.2f})") 
                                for expense in expenses]
    else:
        # If no expenses, display a placeholder message
        form.expense_id.choices = [(-1, "No expenses found. Please create a new expense.")]
    
    # Get all user's receipts
    if current_user.is_admin and request.args.get('all_users') == 'true':
        receipts = Receipt.query.order_by(Receipt.upload_date.desc()).all()
    else:
        receipts = Receipt.query.filter_by(user_id=current_user.id).order_by(Receipt.upload_date.desc()).all()
    
    return render_template('receipts.html', title='Receipt Management', form=form, receipts=receipts, is_admin=current_user.is_admin)

@app.route('/upload_receipt', methods=['POST'])
@login_required
def upload_receipt():
    """Handle receipt upload"""
    form = ReceiptUploadForm()
    
    # Get all user's expenses for dropdown selection (in case of validation error)
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    form.expense_id.choices = [(expense.id, f"{expense.date.strftime('%Y-%m-%d')} - {expense.description} (${expense.amount:.2f})") 
                              for expense in expenses]
    
    if form.validate_on_submit():
        try:
            file = form.receipt_file.data
            filename = secure_filename(file.filename)
            
            # Generate unique filename to avoid collisions
            unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user.id}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Determine if we're creating a new expense or using an existing one
            expense_id = None
            
            if form.create_new_expense.data:
                # Create a new expense with the provided details
                if not form.expense_date.data or not form.expense_description.data or not form.expense_category.data or not form.expense_amount.data:
                    flash('When creating a new expense, all expense fields are required.', 'danger')
                    return redirect(url_for('index'))
                
                # Create the new expense
                new_expense = Expense(
                    date=form.expense_date.data,
                    description=form.expense_description.data,
                    category=form.expense_category.data,
                    amount=form.expense_amount.data,
                    user_id=current_user.id
                )
                
                db.session.add(new_expense)
                db.session.flush()  # This will assign an ID to the new expense
                
                expense_id = new_expense.id
                logger.debug(f"Created new expense with ID: {expense_id}")
            else:
                # Use the selected existing expense
                if not form.expense_id.data:
                    flash('Please select an expense to link the receipt to.', 'danger')
                    return redirect(url_for('index'))
                
                # Verify the expense belongs to the current user
                expense = Expense.query.filter_by(id=form.expense_id.data, user_id=current_user.id).first()
                if not expense:
                    flash('The selected expense does not exist or does not belong to you.', 'danger')
                    return redirect(url_for('index'))
                
                expense_id = form.expense_id.data
            
            # Create receipt record with the expense ID
            receipt = Receipt(
                expense_id=expense_id,
                user_id=current_user.id,
                filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                file_type=file.content_type,
                description=form.description.data
            )
            
            db.session.add(receipt)
            db.session.commit()
            
            flash('Receipt uploaded successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.exception("Error uploading receipt")
            flash(f'Error uploading receipt: {str(e)}', 'danger')
            db.session.rollback()
    else:
        # Handle form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    # On validation failure, return to the receipts page with the form
    receipts = Receipt.query.filter_by(user_id=current_user.id).order_by(Receipt.upload_date.desc()).all()
    return render_template('receipts.html', title='Receipt Management', form=form, receipts=receipts, is_admin=current_user.is_admin)

@app.route('/view_receipt/<int:receipt_id>')
@login_required
def view_receipt(receipt_id):
    """View a specific receipt"""
    receipt = Receipt.query.get_or_404(receipt_id)
    
    # Check if the user has permission to view this receipt
    if receipt.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this receipt.', 'danger')
        return redirect(url_for('index'))
    
    # Send the file from the server
    return send_file(receipt.file_path, 
                    download_name=receipt.filename,
                    as_attachment=False)

@app.route('/delete_receipt/<int:receipt_id>', methods=['POST'])
@login_required
def delete_receipt(receipt_id):
    """Delete a receipt"""
    receipt = Receipt.query.get_or_404(receipt_id)
    
    # Check if the user has permission to delete this receipt
    if receipt.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to delete this receipt.', 'danger')
        return redirect(url_for('receipts'))
    
    try:
        # Delete the file from the filesystem
        if os.path.exists(receipt.file_path):
            os.remove(receipt.file_path)
        
        # Delete the record from the database
        db.session.delete(receipt)
        db.session.commit()
        
        flash('Receipt deleted successfully!', 'success')
    except Exception as e:
        logger.exception("Error deleting receipt")
        flash(f'Error deleting receipt: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('receipts'))


# Conversational AI Assistant routes
@app.route('/ai/conversational')
@login_required
def chat_assistant():
    """Show conversational AI assistant interface"""
    logger.debug(f"Accessing conversational assistant, user: {current_user.username}")
    
    return render_template('ai/chat_assistant.html', title='Conversational Assistant')

@app.route('/ai/process_query', methods=['POST'])
@login_required
def process_ai_query():
    """Process a natural language query and return response"""
    logger.debug(f"Processing AI query, user: {current_user.username}")
    
    # Get query from request
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({
            'success': False,
            'response': 'Empty query provided'
        })
    
    try:
        # Process the query - now returns a dictionary with response and metadata
        result = conversation_assistant.process_query(query)
        
        # Simply return the result dictionary as JSON
        # It already contains 'success' and 'response' keys
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({
            'success': False,
            'response': 'Sorry, there was an error processing your query. Please try again.'
        })

@app.route('/ai/process_audio', methods=['POST'])
@login_required
def process_audio():
    """Process audio recording and convert to text"""
    logger.debug(f"Processing audio recording, user: {current_user.username}")
    
    if 'audio' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No audio file provided'
        })
    
    audio_file = request.files['audio']
    
    if not audio_file:
        return jsonify({
            'success': False,
            'error': 'Empty audio file'
        })
    
    # Define temp_filename outside try block so it's accessible in except block
    temp_filename = os.path.join(UPLOAD_FOLDER, f"temp_audio_{current_user.id}.wav")
    
    try:
        # Save the audio file temporarily
        audio_file.save(temp_filename)
        
        # Use OpenAI Whisper API to transcribe the audio
        if not conversation_assistant.openai_client:
            return jsonify({
                'success': False,
                'error': 'OpenAI API not configured'
            })
        
        with open(temp_filename, "rb") as audio_file:
            transcript = conversation_assistant.openai_client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        
        return jsonify({
            'success': True,
            'text': transcript.text
        })
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        # Clean up the temporary file if it exists
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return jsonify({
            'success': False,
            'error': f"Error processing audio: {str(e)}"
        })

# Old expense forecast route moved to business features section below

# Business Features Routes
@app.route('/business/request_upgrade', methods=['GET', 'POST'])
@login_required
def request_business_upgrade():
    """Request an upgrade to business features."""
    # Check if user already has business access
    if current_user.is_business_user:
        flash('You already have access to business features.', 'info')
        return redirect(url_for('dashboard'))
    
    # Check if user already has a pending request
    existing_request = BusinessUpgradeRequest.query.filter_by(
        user_id=current_user.id, 
        status='pending'
    ).first()
    
    if existing_request:
        flash('You already have a pending business upgrade request.', 'info')
        return redirect(url_for('dashboard'))
    
    form = BusinessUpgradeRequestForm()
    
    if form.validate_on_submit():
        # Create new business upgrade request
        upgrade_request = BusinessUpgradeRequest(
            user_id=current_user.id,
            company_name=form.company_name.data,
            industry=form.industry.data,
            business_email=form.business_email.data,
            phone_number=form.phone_number.data,
            reason=form.reason.data
        )
        
        try:
            db.session.add(upgrade_request)
            db.session.commit()
            
            # Notify user
            flash('Your business upgrade request has been submitted and is pending review.', 'success')
            
            # Create a notification for the user
            notification = UserNotification(
                user_id=current_user.id,
                title='Business Upgrade Request Submitted',
                message='Your request to access business features has been submitted and is pending review.',
                notification_type='info'
            )
            db.session.add(notification)
            
            # Create a notification for admins
            admins = User.query.filter_by(is_admin=True).all()
            for admin in admins:
                admin_notification = UserNotification(
                    user_id=admin.id,
                    title='New Business Upgrade Request',
                    message=f'User {current_user.username} has requested access to business features.',
                    notification_type='info',
                    related_id=upgrade_request.id,
                    related_type='business_upgrade_request'
                )
                db.session.add(admin_notification)
            
            db.session.commit()
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error submitting business upgrade request: {str(e)}")
            flash('An error occurred while submitting your request. Please try again.', 'danger')
    
    return render_template('business/upgrade_request.html', form=form)


@app.route('/admin/business_requests')
@login_required
def admin_business_requests():
    """Admin view for managing business upgrade requests."""
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all business upgrade requests, newest first
    requests = BusinessUpgradeRequest.query.order_by(BusinessUpgradeRequest.created_at.desc()).all()
    
    # Manually add user info to requests to avoid relationship issues
    requests_with_users = []
    for req in requests:
        user = User.query.get(req.user_id)
        if user:
            # Add username attribute to request object
            req.username = user.username
        else:
            req.username = f"User #{req.user_id}"
        requests_with_users.append(req)
    
    return render_template('admin/business_requests.html', requests=requests_with_users)


@app.route('/admin/business_request/<int:request_id>', methods=['GET', 'POST'])
@login_required
def admin_business_request_detail(request_id):
    """View and process a specific business upgrade request."""
    logger.info("===== BUSINESS REQUEST DETAIL DEBUG =====")
    logger.info(f"Request ID: {request_id}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Current user: {current_user.username} (ID: {current_user.id}, Admin: {current_user.is_admin})")
    
    # Check form data for POST requests
    if request.method == 'POST':
        logger.info("POST FIELDS:")
        for key, value in request.form.items():
            logger.info(f"- {key}: {value}")
        
        # Check for CSRF token specifically
        csrf_token = request.form.get('csrf_token')
        logger.info(f"CSRF Token present: {csrf_token is not None}")
    
    if not current_user.is_admin:
        logger.warning(f"Non-admin user tried to access business request: {current_user.username}")
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Get the business upgrade request
        upgrade_request = BusinessUpgradeRequest.query.get_or_404(request_id)
        logger.info(f"Found upgrade request: ID {upgrade_request.id}, Status: {upgrade_request.status}, User ID: {upgrade_request.user_id}")
        
        # Get the requesting user
        user = User.query.get(upgrade_request.user_id)
        if user:
            logger.info(f"Found requesting user: {user.username} (ID: {user.id}, Currently business: {user.is_business_user})")
        else:
            logger.error(f"Could not find user with ID: {upgrade_request.user_id}")
            flash('Could not find the user associated with this request.', 'danger')
            return redirect(url_for('admin_business_requests'))
        
        if request.method == 'POST':
            logger.info("Processing POST request")
            try:
                # Validate CSRF token first
                csrf_token = request.form.get('csrf_token')
                if not csrf_token:
                    logger.error("CSRF token missing from request")
                    flash('CSRF token missing. Please try again.', 'danger')
                    return render_template('admin/business_request_detail.html', request=upgrade_request, user=user)
                
                action = request.form.get('action')
                admin_notes = request.form.get('admin_notes', '')
                
                logger.info(f"Action: {action}, Notes: {admin_notes}")
                
                # Update the request
                upgrade_request.admin_notes = admin_notes
                upgrade_request.handled_by = current_user.id
                upgrade_request.updated_at = datetime.now()
                
                if action == 'approve':
                    logger.info("Approving request")
                    # Approve the request
                    upgrade_request.status = 'approved'
                    
                    # Update user's business status
                    user.is_business_user = True
                    logger.info(f"Set user.is_business_user to {user.is_business_user}")
                    
                    # Create user notification
                    notification = UserNotification(
                        user_id=user.id,
                        title='Business Upgrade Request Approved',
                        message='Your request to access business features has been approved. You now have access to business features.',
                        notification_type='success'
                    )
                    db.session.add(notification)
                    logger.info(f"Created approval notification for user {user.id}")
                    
                elif action == 'reject':
                    logger.info("Rejecting request")
                    # Reject the request
                    upgrade_request.status = 'rejected'
                    
                    # Create user notification
                    notification = UserNotification(
                        user_id=user.id,
                        title='Business Upgrade Request Rejected',
                        message='Your request to access business features has been rejected. Please check the admin notes for more information.',
                        notification_type='warning'
                    )
                    db.session.add(notification)
                    logger.info(f"Created rejection notification for user {user.id}")
                else:
                    logger.error(f"Invalid action: {action}")
                    flash('Invalid action. Please try again.', 'danger')
                    return render_template('admin/business_request_detail.html', request=upgrade_request, user=user)
                
                try:
                    logger.info("Committing changes to database")
                    db.session.commit()
                    logger.info("Database commit successful")
                    flash(f'Business upgrade request has been {upgrade_request.status}.', 'success')
                    
                    # Force refresh to ensure we get the updated data
                    db.session.refresh(user)
                    db.session.refresh(upgrade_request)
                    
                    logger.info(f"After commit - User business status: {user.is_business_user}")
                    logger.info(f"After commit - Request status: {upgrade_request.status}")
                    
                    return redirect(url_for('admin_business_requests'))
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Database commit error: {str(e)}")
                    logger.error(f"Error details: {type(e).__name__}")
                    flash(f'Database error: {str(e)}', 'danger')
                    return render_template('admin/business_request_detail.html', request=upgrade_request, user=user)
            except Exception as e:
                logger.error(f"Error processing form: {str(e)}")
                logger.error(f"Error details: {type(e).__name__}")
                flash(f'Error processing form: {str(e)}', 'danger')
                return render_template('admin/business_request_detail.html', request=upgrade_request, user=user)
    
    except Exception as e:
        logger.error(f"General error in route: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}")
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('admin_business_requests'))
    
    return render_template('admin/business_request_detail.html', request=upgrade_request, user=user)


@app.route('/business/excel_import', methods=['GET', 'POST'])
@login_required
def business_excel_import():
    """Excel import for business users."""
    # Check if user has business access
    if not current_user.is_business_user and not current_user.is_admin:
        flash('You need business user access to import Excel files.', 'warning')
        return redirect(url_for('request_business_upgrade'))
    
    form = ExcelImportForm()
    
    if form.validate_on_submit():
        # Handle file upload
        file = form.excel_file.data
        filename = secure_filename(file.filename)
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.root_path, 'uploads', 'excel')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Create Excel import record
        excel_import = ExcelImport(
            user_id=current_user.id,
            filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            description=form.description.data,
            status='pending'
        )
        
        try:
            db.session.add(excel_import)
            db.session.commit()
            
            # Process the Excel file immediately
            try:
                logger.info(f"Processing Excel import with ID {excel_import.id}")
                if excel_processor.process_excel_import(excel_import.id):
                    flash('Excel file processed successfully!', 'success')
                else:
                    flash('Excel file uploaded but encountered errors during processing. Check the status for details.', 'warning')
            except Exception as e:
                logger.error(f"Error processing Excel import: {str(e)}")
                flash(f'File uploaded but processing failed: {str(e)}', 'warning')
                
            return redirect(url_for('business_excel_import'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating Excel import record: {str(e)}")
            flash('An error occurred while uploading your file. Please try again.', 'danger')
    
    # Get user's previous imports
    previous_imports = ExcelImport.query.filter_by(user_id=current_user.id).order_by(ExcelImport.upload_date.desc()).all()
    
    return render_template('business/excel_import.html', form=form, imports=previous_imports)


@app.route('/migrate/business_tables')
@login_required
def migrate_business_tables():
    """Run business tables migration."""
    if not current_user.is_admin:
        flash('You do not have permission to run migrations.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Import the migration script
        import migrate_business_tables
        
        # Run the migration
        success = migrate_business_tables.main()
        
        if success:
            flash('Business tables migration completed successfully.', 'success')
        else:
            flash('Business tables migration failed. Check the logs for details.', 'danger')
    except Exception as e:
        logger.error(f"Error running business tables migration: {str(e)}")
        flash(f'An error occurred during migration: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))


@app.route('/admin/direct_approve/<int:request_id>')
@login_required
def direct_approve_business_request(request_id):
    """Debug route for direct approval of business upgrade requests."""
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Get the business upgrade request
        upgrade_request = BusinessUpgradeRequest.query.get_or_404(request_id)
        logger.info(f"DIRECT APPROVAL - Request: {upgrade_request.id}, Status: {upgrade_request.status}")
        
        # Get the requesting user
        user = User.query.get(upgrade_request.user_id)
        if not user:
            flash('User not found for this request.', 'danger')
            return redirect(url_for('admin_business_requests'))
            
        logger.info(f"DIRECT APPROVAL - User: {user.username} (ID: {user.id})")
        
        # Update request status
        upgrade_request.status = 'approved'
        upgrade_request.admin_notes = 'Directly approved by admin'
        upgrade_request.handled_by = current_user.id
        upgrade_request.updated_at = datetime.now()
        
        # Update user's business status
        user.is_business_user = True
        logger.info(f"DIRECT APPROVAL - Set is_business_user to {user.is_business_user}")
        
        # Create user notification
        notification = UserNotification(
            user_id=user.id,
            title='Business Upgrade Request Approved',
            message='Your request to access business features has been approved directly. You now have access to business features.',
            notification_type='success'
        )
        db.session.add(notification)
        
        # Commit changes
        db.session.commit()
        logger.info("DIRECT APPROVAL - Database commit successful")
        
        # Log final state
        db.session.refresh(user)
        db.session.refresh(upgrade_request)
        logger.info(f"DIRECT APPROVAL - Final user business status: {user.is_business_user}")
        logger.info(f"DIRECT APPROVAL - Final request status: {upgrade_request.status}")
        
        flash('Business upgrade request has been directly approved.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"DIRECT APPROVAL ERROR: {str(e)}")
        flash(f'Error approving request: {str(e)}', 'danger')
    
    return redirect(url_for('admin_business_requests'))


# Add a check for business users to the AI prediction routes
@app.route('/ai/expense_forecast')
@login_required
def expense_forecast():
    """Generate expense forecast for authenticated user."""
    # Check if AI predictions require business user access and user does not have access
    if not current_user.is_business_user and not current_user.is_admin:
        logger.warning(f"Non-business user {current_user.username} tried to access AI predictions")
        return jsonify({
            'success': False,
            'message': "This feature requires business user access. Please request an upgrade.",
            'data': None
        })
    
    try:
        # Generate the forecast
        forecast = conversation_assistant.get_expense_forecast(
            user_id=current_user.id,
            months_ahead=3
        )
        
        return jsonify({
            'success': True,
            'message': "Forecast generated successfully",
            'data': forecast
        })
    except Exception as e:
        logger.error(f"Error generating expense forecast: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating forecast: {str(e)}",
            'data': None
        })


@app.route('/ai/last_month_predictions')
@login_required
def last_month_predictions():
    """Generate and return predictions based on last month's expenses"""
    # Check if AI predictions require business user access and user does not have access
    if not current_user.is_business_user and not current_user.is_admin:
        logger.warning(f"Non-business user {current_user.username} tried to access AI predictions")
        return jsonify({
            'success': False,
            'message': "This feature requires business user access. Please request an upgrade.",
            'data': None
        })
    
    logger.debug(f"Generating last month predictions, user: {current_user.username}")
    
    try:
        # Generate the predictions
        predictions = conversation_assistant.get_last_month_predictions(
            user_id=current_user.id
        )
        
        return jsonify(predictions)
    except Exception as e:
        logger.error(f"Error generating last month predictions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating predictions: {str(e)}",
            'data': None
        })


@app.route('/ai/funny-chatbot')
@login_required
def funny_chatbot():
    """Show the professional financial assistant interface."""
    # Check if Perplexity API is available
    api_available = perplexity_service.check_api_availability()
    
    # Get top spending categories for the current user
    categories_data = []
    try:
        # Get the current user's expenses (excluding Excel imports)
        expenses = Expense.query.filter_by(user_id=current_user.id, excel_import_id=None).all()
        
        # Calculate category totals
        category_totals = {}
        for expense in expenses:
            if expense.category in category_totals:
                category_totals[expense.category] += expense.amount
            else:
                category_totals[expense.category] = expense.amount
        
        # Sort categories by total amount
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 5 categories
        top_categories = sorted_categories[:5]
        
        # Format for template
        for category, amount in top_categories:
            categories_data.append({
                'name': category,
                'amount': amount
            })
    except Exception as e:
        logger.exception("Error fetching category data for funny chatbot")
    
    # Get a daily financial tip
    daily_tip = perplexity_service.get_financial_tip() if api_available else "Tip of the day: Remember that the best investment you can make is in yourself. And maybe a good coffee machine."
    
    return render_template(
        'ai/funny_chatbot.html',
        title='Financial Assistant',
        api_available=api_available,
        categories_data=categories_data,
        daily_tip=daily_tip
    )


@app.route('/ai/funny-chat', methods=['POST'])
@login_required
def funny_chat_process():
    """Process a query to the professional financial assistant."""
    # Add console output for debugging
    print("===== FUNNY CHAT PROCESS =====")
    print("Received request!")
    
    try:
        data = request.get_json()
        print(f"Request data: {data}")
        
        if not data or 'message' not in data:
            print("Error: Missing message in request")
            return jsonify({
                'success': False,
                'error': 'Missing message',
                'response': 'Please provide a message.'
            })
    except Exception as e:
        print(f"Error parsing request: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to parse request: {str(e)}',
            'response': 'There was an error processing your request. Please try again.'
        })
    
    message = data.get('message', '')
    humor_level = data.get('humor_level', 'medium')
    
    # Get recent expenses for context (limit to last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= thirty_days_ago,
        Expense.excel_import_id == None
    ).order_by(Expense.date.desc()).all()
    
    # Format financial context
    financial_context = None
    if recent_expenses:
        total_spent = sum(expense.amount for expense in recent_expenses)
        avg_expense = total_spent / len(recent_expenses)
        
        # Group by category
        categories = {}
        for expense in recent_expenses:
            if expense.category in categories:
                categories[expense.category] += expense.amount
            else:
                categories[expense.category] = expense.amount
        
        # Sort categories by amount
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        top_categories = sorted_categories[:3]
        
        # Create context
        financial_context = f"""
        User financial context (last 30 days):
        - Total spent: ${total_spent:.2f}
        - Number of expenses: {len(recent_expenses)}
        - Average expense: ${avg_expense:.2f}
        - Top spending categories: {', '.join([f'{cat} (${amt:.2f})' for cat, amt in top_categories])}
        """
    
    # Special case for spending analysis request
    if "my spending" in message.lower():
        response = perplexity_service.analyze_spending_pattern(
            [expense.__dict__ for expense in recent_expenses]
        )
        
        # Add follow-up suggestions
        suggestions = [
            "How can I reduce my spending?",
            "What's my biggest expense?",
            "Give me a saving tip",
            "Compare this month to last month"
        ]
        
        return jsonify({
            'success': True,
            'response': response,
            'suggestions': suggestions
        })
    
    # Process regular query
    try:
        # Log request details for debugging
        logger.info(f"Sending query to Perplexity API: {message[:50]}...")
        
        result = perplexity_service.generate_response(
            query=message,
            financial_context=financial_context,
            humor_level=humor_level
        )
        
        # Log detailed API result for debugging
        logger.debug(f"Perplexity API result: {result}")
    except Exception as e:
        logger.error(f"Error in funny_chat_process: {str(e)}", exc_info=True)
        result = {
            'success': False,
            'error': str(e),
            'response': f"I encountered a technical error: {str(e)}. Please try again later."
        }
    
    # Add follow-up suggestions based on the query type
    suggestions = []
    if "budget" in message.lower():
        suggestions = [
            "How do I create a budget?",
            "What's a good budget breakdown?",
            "How to stick to a budget?",
            "50/30/20 budget rule"
        ]
    elif "save" in message.lower() or "saving" in message.lower():
        suggestions = [
            "Saving money on groceries",
            "Best savings accounts",
            "How much should I save each month?",
            "Emergency fund tips"
        ]
    elif "invest" in message.lower():
        suggestions = [
            "Investment basics",
            "Low-risk investments",
            "What is compound interest?",
            "Retirement planning"
        ]
    elif "food" in message.lower() or "groceries" in message.lower() or "restaurant" in message.lower():
        suggestions = [
            "How to meal plan on a budget?",
            "Best days for grocery shopping",
            "Restaurant hacks to save money",
            "Apps that offer food discounts"
        ]
    
    # If API call failed, use our fallback responses based on query topic
    if not result.get('success', False):
        logger.warning(f"Perplexity API call failed, using fallback response for: {message}")
        
        # Professional financial assistant fallback responses
        if "food" in message.lower() or "groceries" in message.lower():
            response = "Consider implementing meal planning and bulk purchasing to reduce your grocery expenses. Preparing meals at home instead of ordering takeout can save up to 60-70% of your food costs. Creating a shopping list and sticking to it will help avoid impulse purchases."
        elif "budget" in message.lower():
            response = "The 50/30/20 budgeting approach is effective for many households: allocate 50% of income to necessities, 30% to discretionary spending, and 20% to savings and debt reduction. Regular budget reviews help identify areas where adjustments can improve your financial stability."
        elif "save" in message.lower() or "saving" in message.lower():
            response = "Automating your savings is one of the most effective strategies. Set up automatic transfers to your savings account on payday. Consider implementing a 24-hour waiting period for non-essential purchases over $50 to reduce impulse buying and review subscription services regularly."
        elif "invest" in message.lower():
            response = "For beginning investors, diversified index funds typically offer lower risk with reasonable returns. Remember that time in the market is typically more beneficial than trying to time market fluctuations. Consider consulting with a financial advisor for personalized investment strategies."
        elif "expensive" in message.lower() or "spending" in message.lower():
            response = "To manage spending effectively, try tracking all expenses for 30 days to identify patterns. Using cash for discretionary spending can create more awareness of purchases. Setting specific spending limits for each category and reviewing them weekly helps maintain financial discipline."
        elif "credit" in message.lower() or "debt" in message.lower():
            response = "To use credit cards responsibly: pay the full balance each month, keep utilization below 30% of your limit, make payments on time, and select cards with benefits that match your spending patterns. Regularly reviewing your credit report helps maintain your financial reputation."
        elif "coffee" in message.lower() or "latte" in message.lower():
            response = "Small regular purchases like coffee can be maintained if they provide value and fit within your overall budget. Focus on larger expenses and recurring subscriptions for more significant savings. The key is balancing daily enjoyment with long-term financial goals."
        else:
            response = "I apologize for the technical difficulty. While we resolve this, here's a helpful tip: establishing automatic transfers to your savings account on payday ensures consistent progress toward your financial goals before you have a chance to spend those funds."
        
        # Always return true success for fallback responses
        return jsonify({
            'success': True,
            'response': response,
            'suggestions': suggestions,
            'fallback': True  # Flag to indicate this was a fallback response
        })
    
    return jsonify({
        'success': result.get('success', False),
        'response': result.get('response', 'Sorry, I encountered an issue. Please try again later.'),
        'suggestions': suggestions if result.get('success', False) else []
    })


# Routes for downloading sample templates
@app.route('/downloads/excel_template.xlsx')
def download_excel_template():
    """Download Excel template for expense import."""
    try:
        template_path = os.path.join(TEMPLATES_FOLDER, 'expense_import_template.xlsx')
        return send_file(template_path, 
                         as_attachment=True, 
                         download_name='expense_import_template.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logger.error(f"Error downloading Excel template: {str(e)}")
        flash('Error downloading template. Please try again.', 'danger')
        return redirect(url_for('business_excel_import'))

@app.route('/downloads/csv_template.csv')
def download_csv_template():
    """Download CSV template for expense import."""
    try:
        template_path = os.path.join(TEMPLATES_FOLDER, 'expense_import_template.csv')
        return send_file(template_path, 
                         as_attachment=True, 
                         download_name='expense_import_template.csv',
                         mimetype='text/csv')
    except Exception as e:
        logger.error(f"Error downloading CSV template: {str(e)}")
        flash('Error downloading template. Please try again.', 'danger')
        return redirect(url_for('business_excel_import'))


@app.route('/business/process_pending_imports')
@login_required
def process_pending_imports():
    """Process all pending imports."""
    if not current_user.is_business_user and not current_user.is_admin:
        flash('You need business user access to process imports.', 'warning')
        return redirect(url_for('request_business_upgrade'))
    
    try:
        # Process pending imports
        count = excel_processor.process_pending_imports()
        
        if count > 0:
            flash(f'Successfully processed {count} pending imports.', 'success')
        else:
            flash('No pending imports to process.', 'info')
    except Exception as e:
        logger.error(f"Error processing pending imports: {str(e)}")
        flash(f'Error processing imports: {str(e)}', 'danger')
    
    return redirect(url_for('business_excel_import'))


@app.route('/business/import_details/<int:import_id>')
@login_required
def import_details(import_id):
    """Show details of an Excel import including the expenses created."""
    if not current_user.is_business_user and not current_user.is_admin:
        flash('You need business user access to view import details.', 'warning')
        return redirect(url_for('request_business_upgrade'))
    
    # Get the import record
    excel_import = ExcelImport.query.get_or_404(import_id)
    
    # Check if the import belongs to the current user or if the user is an admin
    if excel_import.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this import.', 'danger')
        return redirect(url_for('business_excel_import'))
    
    # Get expenses created by this import
    expenses = Expense.query.filter_by(excel_import_id=import_id).order_by(Expense.date.desc()).all()
    
    return render_template('business/import_details.html', 
                           excel_import=excel_import,
                           expenses=expenses,
                           title='Import Details')


@app.route('/business/excel_visualize', methods=['GET', 'POST'])
@login_required
def excel_visualize():
    """Excel visualization for business users."""
    # Check if user has business access
    if not current_user.is_business_user and not current_user.is_admin:
        flash('You need business user access to visualize Excel data.', 'warning')
        return redirect(url_for('request_business_upgrade'))
    
    form = ExcelImportForm()
    result = None
    
    # Get all completed imports for this user
    imports = ExcelImport.query.filter_by(
        user_id=current_user.id, 
        status='completed'
    ).order_by(ExcelImport.upload_date.desc()).all()
    
    if form.validate_on_submit():
        try:
            # Handle file upload
            file = form.excel_file.data
            filename = secure_filename(file.filename)
            
            # Create upload directory if it doesn't exist
            os.makedirs(EXCEL_UPLOAD_FOLDER, exist_ok=True)
            
            # Create a unique filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(EXCEL_UPLOAD_FOLDER, unique_filename)
            
            # Save the file
            file.save(file_path)
            
            # Process the file for visualization
            output_file = excel_visualizer.analyze_excel_file(file_path)
            
            if output_file:
                # Prepare chart data for display
                temp_dir = 'temp_charts'
                chart_paths = [
                    {'title': 'Expenses by Category', 'path': f'/temp_charts/category_pie.png'},
                    {'title': 'Daily Expenses Over Time', 'path': f'/temp_charts/time_series.png'},
                    {'title': 'Expenses by Payment Method', 'path': f'/temp_charts/payment_method.png'},
                    {'title': 'Top Merchants by Expense', 'path': f'/temp_charts/merchant.png'},
                    {'title': 'Category Expense Trends', 'path': f'/temp_charts/category_trend.png'}
                ]
                
                # Filter out any charts that weren't generated
                chart_paths = [chart for chart in chart_paths if os.path.exists(os.path.join(TEMP_CHARTS_FOLDER, os.path.basename(chart['path'])))]
                
                result = {
                    'filename': os.path.basename(output_file),
                    'path': output_file,
                    'charts': chart_paths
                }
                
                flash('Excel file analyzed successfully!', 'success')
            else:
                flash('Error analyzing the Excel file. Please check the file format.', 'danger')
                
        except Exception as e:
            logger.exception("Error visualizing Excel file")
            flash(f'Error analyzing Excel file: {str(e)}', 'danger')
    
    return render_template(
        'business/excel_visualize.html',
        form=form,
        imports=imports,
        result=result
    )


@app.route('/business/excel_visualize/import/<int:import_id>')
@login_required
def excel_visualize_from_import(import_id):
    """Visualize an existing Excel import."""
    # Check if user has business access
    if not current_user.is_business_user and not current_user.is_admin:
        flash('You need business user access to visualize Excel data.', 'warning')
        return redirect(url_for('request_business_upgrade'))
    
    # Get the import record
    excel_import = ExcelImport.query.get_or_404(import_id)
    
    # Ensure user can only access their own imports (unless admin)
    if excel_import.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to visualize this import.', 'danger')
        return redirect(url_for('business_excel_import'))
    
    # Check if import status is completed
    if excel_import.status != 'completed':
        flash('This import is not completed yet. Cannot generate visualizations.', 'warning')
        return redirect(url_for('excel_visualize'))
    
    try:
        # Get the file path
        file_path = os.path.join(EXCEL_UPLOAD_FOLDER, excel_import.filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            flash('Excel file not found. The file may have been deleted.', 'danger')
            return redirect(url_for('excel_visualize'))
        
        # Process the file for visualization
        output_file = excel_visualizer.analyze_excel_file(file_path)
        
        if output_file:
            # Prepare chart data for display
            temp_dir = 'temp_charts'
            chart_paths = [
                {'title': 'Expenses by Category', 'path': f'/temp_charts/category_pie.png'},
                {'title': 'Daily Expenses Over Time', 'path': f'/temp_charts/time_series.png'},
                {'title': 'Expenses by Payment Method', 'path': f'/temp_charts/payment_method.png'},
                {'title': 'Top Merchants by Expense', 'path': f'/temp_charts/merchant.png'},
                {'title': 'Category Expense Trends', 'path': f'/temp_charts/category_trend.png'}
            ]
            
            # Filter out any charts that weren't generated
            chart_paths = [chart for chart in chart_paths if os.path.exists(os.path.join(TEMP_CHARTS_FOLDER, os.path.basename(chart['path'])))]
            
            result = {
                'filename': os.path.basename(output_file),
                'path': output_file,
                'charts': chart_paths
            }
            
            # Get all completed imports for this user (for the sidebar)
            imports = ExcelImport.query.filter_by(
                user_id=current_user.id, 
                status='completed'
            ).order_by(ExcelImport.upload_date.desc()).all()
            
            form = ExcelImportForm()
            
            flash('Excel file analyzed successfully!', 'success')
            return render_template(
                'business/excel_visualize.html',
                form=form,
                imports=imports,
                result=result
            )
        else:
            flash('Error analyzing the Excel file. Please check the file format.', 'danger')
            return redirect(url_for('excel_visualize'))
            
    except Exception as e:
        logger.exception("Error visualizing Excel file")
        flash(f'Error analyzing Excel file: {str(e)}', 'danger')
        return redirect(url_for('excel_visualize'))


@app.route('/business/excel_visualize/download/<filename>')
@login_required
def download_visualization(filename):
    """Download a visualization Excel file."""
    # Check if user has business access
    if not current_user.is_business_user and not current_user.is_admin:
        flash('You need business user access to download visualization files.', 'warning')
        return redirect(url_for('request_business_upgrade'))
    
    try:
        return send_from_directory(
            EXCEL_UPLOAD_FOLDER,
            filename,
            as_attachment=True
        )
    except Exception as e:
        logger.exception("Error downloading visualization file")
        flash(f'Error downloading file: {str(e)}', 'danger')
        return redirect(url_for('excel_visualize'))


@app.route('/temp_charts/<path:filename>')
def serve_chart(filename):
    """Serve chart images from the temp_charts directory."""
    return send_from_directory(TEMP_CHARTS_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
