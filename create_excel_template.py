"""
Create an Excel template for expense import.
"""

import pandas as pd
from openpyxl.styles import Font

# Sample data
data = {
    'date': ['2025-04-01', '2025-04-02', '2025-04-03', '2025-04-04', '2025-04-05'],
    'amount': [45.99, 12.50, 89.99, 25.75, 199.99],
    'category': ['Groceries', 'Transportation', 'Entertainment', 'Dining', 'Shopping'],
    'description': ['Weekly grocery shopping', 'Bus fare', 'Concert tickets', 'Lunch with colleagues', 'New headphones'],
    'payment_method': ['Credit Card', 'Cash', 'Credit Card', 'Debit Card', 'Credit Card'],
    'merchant': ['Whole Foods', 'Metro Transit', 'Ticketmaster', 'Cafe Bistro', 'Electronics Store']
}

# Create DataFrame
df = pd.DataFrame(data)

# Create Excel writer
excel_path = 'static/templates/expense_import_template.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Expenses')
    
    # Access the workbook and the worksheet
    workbook = writer.book
    worksheet = writer.sheets['Expenses']
    
    # Format headers with bold font
    for col_num, column_title in enumerate(df.columns):
        cell = worksheet.cell(row=1, column=col_num+1)
        cell.font = Font(bold=True)

print(f"Excel template created at {excel_path}")