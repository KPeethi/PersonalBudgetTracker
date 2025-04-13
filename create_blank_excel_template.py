"""
Create a blank Excel template for expense import without sample data.
"""

import pandas as pd
from openpyxl.styles import Font

# Create an empty DataFrame with just the column headers
columns = ['date', 'amount', 'category', 'description', 'payment_method', 'merchant']
df = pd.DataFrame(columns=columns)

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

print(f"Blank Excel template created at {excel_path}")