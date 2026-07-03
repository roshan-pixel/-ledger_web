import sqlite3
import win32com.client
import pythoncom
import json
import math
import os

DB_PATH = 'ledger.db'

def clean_val(val):
    if val is None:
        return ""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return ""
    if type(val).__name__ == 'time':
        return str(val)
    if hasattr(val, 'Format'):
        return str(val)
    return val

def migrate():
    print("Starting migration to SQLite...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)''')
    
    # inventory table: c1 to c30
    cols = ["c{} TEXT".format(i) for i in range(1, 31)]
    c.execute(f'''CREATE TABLE inventory (row_num INTEGER PRIMARY KEY, {", ".join(cols)})''')
    
    c.execute('''CREATE TABLE customers (
        ds_code TEXT PRIMARY KEY, ds_name TEXT, mobile TEXT, address TEXT, 
        shipping_address TEXT, shipping_mobile TEXT, shipping_pincode TEXT, last_invoice TEXT
    )''')
    
    c.execute('''CREATE TABLE kpis (key TEXT PRIMARY KEY, value TEXT)''')
    
    pythoncom.CoInitialize()
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    
    excel_path = r'C:\Users\sgarm\Downloads\Asclepius_Wellness_PROFESSIONAL.xlsm'
    wb = excel.Workbooks.Open(excel_path)
    
    try:
        # 1. Migrate Inventory
        print("Migrating Inventory...")
        ws_inv = wb.Sheets('Inventory_Master')
        
        # Headers (row 4, cols 1-30)
        headers = ws_inv.Range(ws_inv.Cells(4, 1), ws_inv.Cells(4, 30)).Value[0]
        cleaned_headers = [str(clean_val(h)).strip() for h in headers]
        c.execute("INSERT INTO settings (key, value) VALUES ('inventory_headers', ?)", (json.dumps(cleaned_headers),))
        
        # Data (rows 5 to 300)
        data = ws_inv.Range(ws_inv.Cells(5, 1), ws_inv.Cells(300, 30)).Value
        for i, row in enumerate(data):
            row_num = i + 5
            cleaned_row = [str(clean_val(v)).strip() for v in row]
            
            # skip completely empty rows (checking Product Name which is col 3, index 2)
            if not cleaned_row[2]:
                continue
                
            placeholders = ", ".join(["?"] * 30)
            c.execute(f"INSERT INTO inventory (row_num, {', '.join([f'c{j}' for j in range(1, 31)])}) VALUES (?, {placeholders})", [row_num] + cleaned_row)
            
        # 2. Migrate Customers
        print("Migrating Customers...")
        ws_cust = wb.Sheets('Customer_Profile')
        cust_data = ws_cust.Range(ws_cust.Cells(2, 1), ws_cust.Cells(1000, 8)).Value
        for row in cust_data:
            ds_code = str(clean_val(row[0])).strip().upper()
            if not ds_code:
                continue
            c.execute('''INSERT OR REPLACE INTO customers 
                         (ds_code, ds_name, mobile, address, shipping_address, shipping_mobile, shipping_pincode, last_invoice) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (ds_code, str(clean_val(row[1])), str(clean_val(row[2])), str(clean_val(row[3])), 
                       str(clean_val(row[4])), str(clean_val(row[5])), str(clean_val(row[6])), str(clean_val(row[7]))))
                       
        # 3. Migrate KPIs
        print("Migrating KPIs...")
        ws_kpi = wb.Sheets('_KPI_Data')
        kpi_data = ws_kpi.Range(ws_kpi.Cells(2, 1), ws_kpi.Cells(20, 2)).Value
        for row in kpi_data:
            key = str(clean_val(row[0])).strip()
            val = str(clean_val(row[1])).strip()
            if key:
                c.execute("INSERT OR REPLACE INTO kpis (key, value) VALUES (?, ?)", (key, val))
                
        ws_dash = wb.Sheets('Dashboard')
        period = str(clean_val(ws_dash.Cells(2, 8).Value)).strip()
        c.execute("INSERT OR REPLACE INTO kpis (key, value) VALUES ('Reporting Period', ?)", (period,))
        
        conn.commit()
        print("Migration complete!")
        
    finally:
        wb.Close(False)
        excel.Quit()
        conn.close()

if __name__ == '__main__':
    migrate()
