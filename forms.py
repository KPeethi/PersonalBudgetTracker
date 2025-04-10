"""
Forms module for the Expense Tracker application.
Defines the forms used in the application.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, Optional
from models import User

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=20)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6)
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password')
    ])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        """Validate that username is unique."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        """Validate that email is unique."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one.')

class LoginForm(FlaskForm):
    """Form for user login."""
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ExpenseForm(FlaskForm):
    """Form for adding/editing expenses."""
    date = DateField('Date', validators=[
        DataRequired()
    ])
    description = StringField('Description', validators=[
        DataRequired(),
        Length(min=1, max=255)
    ])
    category = StringField('Category', validators=[
        DataRequired(),
        Length(min=1, max=100)
    ])
    amount = FloatField('Amount ($)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than 0')
    ])
    submit = SubmitField('Add Expense')

class ReceiptUploadForm(FlaskForm):
    """Form for uploading expense receipts."""
    receipt_file = FileField('Receipt File', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Only images (JPG, PNG) and PDF files are allowed.')
    ])
    # Option to select from existing expenses
    expense_id = SelectField('Link to Expense', coerce=int, validators=[Optional()])
    
    # Option to create a new expense
    create_new_expense = BooleanField('Create New Expense')
    expense_date = DateField('Expense Date', validators=[Optional()])
    expense_description = StringField('Expense Description', validators=[Optional(), Length(min=1, max=255)])
    expense_category = StringField('Category', validators=[Optional(), Length(min=1, max=100)])
    expense_amount = FloatField('Amount ($)', validators=[Optional(), NumberRange(min=0.01, message='Amount must be greater than 0')])
    
    description = TextAreaField('Receipt Description', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Upload Receipt')


class BudgetForm(FlaskForm):
    """Form for setting budget values."""
    # Monthly total budget
    total_budget = FloatField('Total Monthly Budget', validators=[
        DataRequired(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    
    # Category budgets
    food = FloatField('Food & Dining', validators=[
        DataRequired(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    transportation = FloatField('Transportation', validators=[
        DataRequired(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    entertainment = FloatField('Entertainment', validators=[
        DataRequired(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    bills = FloatField('Bills & Utilities', validators=[
        DataRequired(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    shopping = FloatField('Shopping', validators=[
        DataRequired(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    other = FloatField('Other Expenses', validators=[
        DataRequired(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    
    # Custom category fields
    custom_category_name = StringField('Custom Category Name', validators=[
        Optional(),
        Length(min=1, max=50)
    ])
    custom_category_amount = FloatField('Custom Category Amount', validators=[
        Optional(),
        NumberRange(min=0, message='Budget must be a positive number')
    ])
    
    submit = SubmitField('Save Budget')