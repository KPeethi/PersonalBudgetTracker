# Expense Tracker

A comprehensive expense tracking application that helps you manage and analyze your daily expenses.

## Features

- **Web and CLI Interface**: Choose between a modern web interface or a command-line interface
- **Expense Management**: Add, view, and delete expense records
- **Categorization**: Organize expenses by custom categories
- **Monthly Summaries**: View expense totals by month
- **Data Filtering**: Filter expenses by category
- **PostgreSQL Database**: Reliable data storage with PostgreSQL

## Technologies Used

- **Python**: Core programming language
- **Flask**: Web framework for the web interface
- **SQLAlchemy**: ORM for database interactions
- **PostgreSQL**: Database for persistent storage
- **Bootstrap**: Front-end framework for responsive design

## Getting Started

### Web Interface

```bash
python main.py
```

Then visit http://localhost:5000 in your web browser.

### CLI Interface

```bash
python expense_tracker.py
```

## Usage

### Web Interface

1. **Add Expense**: Fill out the form on the homepage
2. **View Expenses**: All expenses are displayed on the homepage
3. **Filter by Category**: Click on a category name to filter expenses
4. **View Monthly Summary**: Click on "Monthly Summary" in the navigation bar
5. **Delete Expense**: Click the "Delete" button next to an expense

### CLI Interface

The CLI provides a menu-driven interface:

1. Add Expense
2. View All Expenses
3. View Expenses by Category
4. View Monthly Summary
5. Exit

## Future Enhancements

- Data visualization with charts
- Export data to CSV/Excel
- Budget planning and tracking
- Multi-user support
- Mobile app integration