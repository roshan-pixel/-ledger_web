import sqlite3
import gspread
import json

def init_google_sheets():
    print("Connecting to Google Sheets...")
    gc = gspread.service_account(filename='credentials.json')
    sheet = gc.open('Ledger_Database')
    
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Inventory
    print("Uploading Inventory...")
    try:
        inv_ws = sheet.worksheet('Inventory')
    except gspread.exceptions.WorksheetNotFound:
        inv_ws = sheet.add_worksheet('Inventory', rows=1000, cols=40)
    
    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    headers = json.loads(c.fetchone()[0])
    
    c.execute("SELECT * FROM inventory ORDER BY row_num")
    rows = c.fetchall()
    
    sheet_data = [headers]
    for r in rows:
        # SQLite row to list based on columns c1..c30
        row_data = [r[f'c{i+1}'] for i in range(len(headers))]
        sheet_data.append(row_data)
        
    inv_ws.clear()
    inv_ws.update(values=sheet_data, range_name='A1')
    
    # 2. Customers
    print("Uploading Customers...")
    try:
        cust_ws = sheet.worksheet('Customers')
    except gspread.exceptions.WorksheetNotFound:
        cust_ws = sheet.add_worksheet('Customers', rows=1000, cols=10)
        
    c.execute("SELECT * FROM customers")
    rows = c.fetchall()
    cust_headers = ['DS Code', 'DS Name', 'Mobile', 'Address', 'Shipping Address', 'Shipping Mobile', 'Shipping Pincode', 'Last Invoice Date']
    sheet_data = [cust_headers]
    for r in rows:
        sheet_data.append([
            r['ds_code'], r['ds_name'], r['mobile'], r['address'], r['shipping_address'],
            r['shipping_mobile'], r['shipping_pincode'], r['last_invoice']
        ])
    cust_ws.clear()
    cust_ws.update(values=sheet_data, range_name='A1')
    
    # 3. KPIs
    print("Uploading KPIs...")
    try:
        kpi_ws = sheet.worksheet('KPIs')
    except gspread.exceptions.WorksheetNotFound:
        kpi_ws = sheet.add_worksheet('KPIs', rows=50, cols=2)
        
    c.execute("SELECT key, value FROM kpis")
    rows = c.fetchall()
    sheet_data = [['Key', 'Value']]
    for r in rows:
        sheet_data.append([r['key'], r['value']])
    kpi_ws.clear()
    kpi_ws.update(values=sheet_data, range_name='A1')
    
    # 4. Invoices
    print("Uploading Invoices...")
    try:
        inv_ws = sheet.worksheet('Invoices')
    except gspread.exceptions.WorksheetNotFound:
        inv_ws = sheet.add_worksheet('Invoices', rows=1000, cols=10)
        
    c.execute("SELECT * FROM invoices")
    rows = c.fetchall()
    sheet_data = [['ID', 'Customer Name', 'Amount', 'Date Created', 'Customer ID']]
    for r in rows:
        sheet_data.append([r['id'], r['customer_name'], r['amount'], r['date_created'], r['customer_id']])
    inv_ws.clear()
    inv_ws.update(values=sheet_data, range_name='A1')
    
    # Remove default 'Sheet1' if it exists
    try:
        sheet1 = sheet.worksheet('Sheet1')
        sheet.del_worksheet(sheet1)
    except:
        pass

    print("Successfully uploaded local database to Google Sheets!")

if __name__ == "__main__":
    init_google_sheets()
