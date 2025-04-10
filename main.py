from flask import render_template, request, redirect, url_for, flash, jsonify, session, Response, send_file, make_response
from markupsafe import Markup
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, timedelta
from functools import wraps
import logging
import json
import calendar
import csv
import io
import os
from werkzeug.utils import secure_filename
from app import app, db
from models import User, Expense, UserPreference, Budget, UserNotification, Receipt
from forms import RegistrationForm, LoginForm, ExpenseForm, ReceiptUploadForm
import plaid_service
import visualization
import suggestions
import ai_assistant

# Directory for storing uploaded receipts
UPLOAD_FOLDER = 'static/uploads/receipts'
# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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
    return Markup(text.replace('\n', '<br>'))


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

    if current_user.is_authenticated:
        # Filter expenses for logged-in user
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
            Expense.date.desc()).all()
        # Get categories for this user
        categories = db.session.query(Expense.category).filter_by(
            user_id=current_user.id).distinct().order_by(
                Expense.category).all()
    else:
        # For non-authenticated users, show a simple welcome message instead of expenses
        expenses = []
        # Empty categories for non-authenticated users
        categories = []

    category_list = [cat[0] for cat in categories]
    today_date = datetime.today().strftime('%Y-%m-%d')
    return render_template('index.html',
                           expenses=expenses,
                           categories=category_list,
                           today_date=today_date,
                           form=form)


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

    if current_user.is_authenticated:
        # Filter by category AND user
        expenses = Expense.query.filter_by(category=category,
                                           user_id=current_user.id).order_by(
                                               Expense.date.desc()).all()
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
                           form=form)


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
            db.func.sum(Expense.amount).label('total_amount')).group_by(
                db.func.extract('year', Expense.date),
                db.func.extract('month', Expense.date)).order_by(
                    db.func.extract('year', Expense.date).desc(),
                    db.func.extract('month', Expense.date).desc()).all()

        # Get expenses grouped by category for each month
        category_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            Expense.category,
            db.func.sum(Expense.amount).label('category_amount')).group_by(
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
                Expense.user_id == user_id).group_by(
                    db.func.extract('year', Expense.date),
                    db.func.extract('month', Expense.date)).order_by(
                        db.func.extract('year', Expense.date).desc(),
                        db.func.extract('month', Expense.date).desc()).all()

        # Get expenses grouped by category for each month
        category_data = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            Expense.category,
            db.func.sum(Expense.amount).label('category_amount')).filter(
                Expense.user_id == user_id).group_by(
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
            db.extract('year', Expense.date) == today.year).scalar() or 0
    else:
        ytd_total = db.session.query(db.func.sum(Expense.amount)).filter(
            db.extract('year', Expense.date) == today.year, Expense.user_id
            == current_user.id).scalar() or 0

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
            base_query = Expense.query.filter_by(user_id=user_id)
        else:
            base_query = Expense.query
    else:
        # Regular users can only see their own expenses
        base_query = Expense.query.filter_by(user_id=current_user.id)
    
    # Get the complete list for total calculations and charts
    expenses = base_query.all()

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
        # For admin viewing all expenses
        monthly_data_query = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount'),
            db.func.count(Expense.id).label('count')).group_by(
                db.func.extract('year', Expense.date),
                db.func.extract('month', Expense.date)).order_by(
                    db.func.extract('year', Expense.date).desc(),
                    db.func.extract('month', Expense.date).desc())
    else:
        # For regular users or admin viewing specific user
        user_id = request.args.get(
            'user_id') if current_user.is_admin else current_user.id
        monthly_data_query = db.session.query(
            db.func.extract('month', Expense.date).label('month'),
            db.func.extract('year', Expense.date).label('year'),
            db.func.sum(Expense.amount).label('total_amount'),
            db.func.count(Expense.id).label('count')).filter(
                Expense.user_id == user_id).group_by(
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
    
    # Use the new dashboard template
    return render_template(
        'dashboard_new.html',
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
        # Pagination variables
        total_items=total_items,
        per_page=per_page,
        current_page=page)


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
@app.route('/ai')
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
    if categories:
        sorted_categories = sorted(categories.items(),
                                   key=lambda x: x[1],
                                   reverse=True)
        for name, amount in sorted_categories[:5]:
            percentage = (amount / total_amount *
                          100) if total_amount > 0 else 0
            top_categories.append({
                'name': name,
                'amount': amount,
                'percentage': percentage
            })

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
    if categories:
        sorted_categories = sorted(categories.items(),
                                   key=lambda x: x[1],
                                   reverse=True)
        for name, amount in sorted_categories[:5]:
            percentage = (amount / total_amount *
                          100) if total_amount > 0 else 0
            top_categories.append({
                'name': name,
                'amount': amount,
                'percentage': percentage
            })

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
                    return redirect(url_for('receipts'))
                
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
                    return redirect(url_for('receipts'))
                
                # Verify the expense belongs to the current user
                expense = Expense.query.filter_by(id=form.expense_id.data, user_id=current_user.id).first()
                if not expense:
                    flash('The selected expense does not exist or does not belong to you.', 'danger')
                    return redirect(url_for('receipts'))
                
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
            return redirect(url_for('receipts'))
            
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
        return redirect(url_for('receipts'))
    
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
