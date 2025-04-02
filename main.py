from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import logging
from app import app, db
from models import Expense

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)