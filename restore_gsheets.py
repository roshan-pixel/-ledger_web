import sqlite3
import gspread
import json
import os
import time

def ensure_sync_log_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT,
                    timestamp REAL,
                    status TEXT
                 )''')
    conn.commit()

def get_last_sync_time(conn, sync_type):
    c = conn.cursor()
    c.execute("SELECT MAX(timestamp) FROM sync_log WHERE sync_type = ? AND status = 'success'", (sync_type,))
    res = c.fetchone()
    return res[0] if res and res[0] else 0

def log_sync(conn, sync_type, status):
    c = conn.cursor()
    c.execute("INSERT INTO sync_log (sync_type, timestamp, status) VALUES (?, ?, ?)", (sync_type, time.time(), status))
    conn.commit()

def restore_from_gsheets():
    print("Restoring database from Google Sheets...")
    conn = sqlite3.connect('ledger.db')
    
    try:
        ensure_sync_log_table(conn)
        
        # Rate limit: 60 seconds
        last_sync = get_last_sync_time(conn, 'restore')
        if time.time() - last_sync < 60:
            print("Restore skipped: last restore was less than 60 seconds ago.")
            conn.close()
            return
            
        creds_path = '/etc/secrets/credentials.json' if os.path.exists('/etc/secrets/credentials.json') else 'credentials.json'
        gc = gspread.service_account(filename=creds_path)
        sheet = gc.open('Ledger_Database')
        
        c = conn.cursor()
        
        # We will hold all inserts in memory and only commit if EVERYTHING succeeds.
        # This prevents partial wipes on API failure.
        
        # 1. Customers
        try:
            cust_ws = sheet.worksheet('Customers')
            cust_data = cust_ws.get_all_values()
            if len(cust_data) > 1:
                c.execute("DELETE FROM customers")
                for row in cust_data[1:]:
                    while len(row) < 8: row.append('')
                    c.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)", row)
        except Exception as e:
            print("Error restoring customers:", e)
            raise e # Fail the transaction
            
        # 2. Inventory
        try:
            inv_ws = sheet.worksheet('Inventory')
            inv_data = inv_ws.get_all_values()
            if len(inv_data) > 1:
                c.execute("DELETE FROM inventory")
                headers = inv_data[0]
                for idx, row in enumerate(inv_data[1:]):
                    while len(row) < len(headers):
                        row.append('')
                    
                    cols = ', '.join([f'c{i+1}' for i in range(len(headers))])
                    placeholders = ', '.join(['?'] * len(headers))
                    
                    c.execute(f"INSERT INTO inventory (row_num, {cols}) VALUES (?, {placeholders})", [idx+1] + row)
        except Exception as e:
            print("Error restoring inventory:", e)
            raise e
            
        # 3. KPIs
        try:
            kpi_ws = sheet.worksheet('KPIs')
            kpi_data = kpi_ws.get_all_values()
            if len(kpi_data) > 1:
                c.execute("DELETE FROM kpis")
                for row in kpi_data[1:]:
                    while len(row) < 2: row.append('')
                    c.execute("INSERT INTO kpis VALUES (?,?)", row)
        except Exception as e:
            print("Error restoring KPIs:", e)
            raise e
            
        # 4. Invoices
        try:
            inv_ws = sheet.worksheet('Invoices')
            inv_data = inv_ws.get_all_values()
            if len(inv_data) > 1:
                c.execute("DELETE FROM invoices")
                for row in inv_data[1:]:
                    while len(row) < 11: row.append('')
                    
                    if row[1] and str(row[1]).startswith("'"):
                        row[1] = str(row[1]).lstrip("'")
                        
                    if row[9] == '': row[9] = 0
                        
                    c.execute("INSERT INTO invoices (id, invoice_no, ds_code, customer_name, amount, date_created, items, status, total_sp, is_dispatched, remark) VALUES (?,?,?,?,?,?,?,?,?,?,?)", row[:11])
        except Exception as e:
            print("Error restoring Invoices:", e)
            raise e
            
        conn.commit()
        log_sync(conn, 'restore', 'success')
        print("Restore complete! Now running sales re-sync...")
        
        # ALWAYS recompute Sold Qty from local invoices table after restore!
        # Because the google sheet might have old/stale Sold Qty columns!
        from sync_sales_to_inventory import sync_sales_to_inventory
        sync_sales_to_inventory(push_to_gsheets=False)
        
        conn.close()
        
    except Exception as e:
        try:
            conn.rollback()
            log_sync(conn, 'restore', 'failed')
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
        print("Fatal error in restore, rolled back:", e)

if __name__ == "__main__":
    restore_from_gsheets()
