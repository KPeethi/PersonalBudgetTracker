# Expense Tracker

A comprehensive financial management application that helps you track, analyze, and optimize your personal expenses.

## Features

- **Multi-Platform Access**: Modern web interface and traditional command-line interface
- **Expense Management**: Add, view, edit, and delete expense records
- **User Authentication**: Secure login and registration with role-based access control
- **Admin Dashboard**: Administrative tools for user and data management
- **Custom Categorization**: Organize expenses with your own category system
- **Data Visualization**: Interactive charts and graphs powered by Plotly
- **Monthly Summaries**: Track spending patterns over time
- **Smart Suggestions**: Get personalized financial recommendations based on your spending habits
- **AI-Powered Analysis**: Leverage AI to gain deeper insights into your financial behavior
- **Data Import**: Easily import transactions from your bank via Plaid API
- **Data Export**: Download your expense data as CSV for external analysis
- **Database Flexibility**: Works with PostgreSQL (default) or MySQL

## Technologies Used

- **Python**: Core programming language
- **Flask**: Web framework with Jinja2 templating
- **SQLAlchemy**: ORM for database interactions
- **PostgreSQL/MySQL**: Flexible database options
- **Bootstrap**: Responsive front-end design
- **Plotly**: Interactive data visualization
- **Pandas**: Data analysis and manipulation
- **Plaid API**: Secure financial data integration
- **OpenAI GPT-4**: AI-powered financial insights
- **Flask-Login**: User authentication management

## Installation

For detailed installation instructions, see [INSTALLATION.md](INSTALLATION.md).

### Quick Start

```bash
# Start the web application
python main.py

# Or use the command-line interface
python expense_tracker.py
```

## Usage

### Web Interface

1. **Register/Login**: Create an account or log in to access your personal dashboard
2. **Add Expenses**: Record new expenses with date, amount, category, and description
3. **View Dashboard**: See your spending patterns with interactive charts
4. **Filter & Search**: Find specific expenses by category, date, or keywords
5. **Import Data**: Connect to your bank accounts via the Plaid integration
6. **Export Data**: Download your expense data as CSV files
7. **Get Insights**: Receive AI-powered analysis and recommendations
8. **Administration**: Manage users and system settings (admin users only)

### CLI Interface

The command-line interface provides these options:

1. Add Expense
2. View All Expenses
3. View Expenses by Category
4. View Monthly Summary
5. Exit

## User Roles

- **Regular Users**: Can manage their own expenses and access personal analytics
- **Administrators**: Can manage all users, view system-wide data, and configure settings

## Configuration

The application is highly configurable through the `config.py` file, allowing you to:

- Choose between PostgreSQL and MySQL databases
- Configure Plaid API credentials for bank integration
- Set up OpenAI API for AI-powered analysis
- Adjust security settings for production environments

## Security Features

- Secure password hashing with Werkzeug
- CSRF protection on all forms
- Environment variable management for sensitive credentials
- Session security configuration for production environments

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open-source software.
