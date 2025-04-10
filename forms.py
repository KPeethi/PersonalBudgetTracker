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
    expense_id = SelectField('Link to Expense (Required)', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Upload Receipt')