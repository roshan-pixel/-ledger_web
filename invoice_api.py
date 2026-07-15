from flask import Blueprint, request, jsonify
import sqlite3
import datetime
import json
import threading
from init_gsheets import init_google_sheets

def get_sold_qty_col_idx(all_headers, date_str):
    sold_cols = []
    for i, h in enumerate(all_headers):
        if str(h).startswith("Sold Qty"):
            sold_cols.append(i + 1)
    if not sold_cols:
        return None
        
    try:
        # Special one-time exemption for 30/06/2026
        if date_str and date_str.startswith('30/06/2026'):
            day = 1
        elif 'T' in date_str:
            dt = datetime.datetime.fromisoformat(date_str)
            day = dt.day
        elif '/' in date_str:
            dt = datetime.datetime.strptime(date_str[:10], '%d/%m/%Y')
            day = dt.day
        else:
            dt = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
            day = dt.day
    except:
        day = datetime.datetime.now().day
        
    if day <= 7: week_idx = 0
    elif day <= 14: week_idx = 1
    elif day <= 21: week_idx = 2
    elif day <= 28: week_idx = 3
    else: week_idx = 4
    
    if week_idx < len(sold_cols):
        return sold_cols[week_idx]
    return sold_cols[-1]


invoice_api = Blueprint('invoice_api', __name__)

@invoice_api.route('/api/invoice/sync_sheets', methods=['POST'])
def sync_sheets_api():
    try:
        from init_gsheets import init_google_sheets
        init_google_sheets()
        return jsonify({'success': True}), 200
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

DB_PATH = 'ledger.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Create invoices table
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT,
            ds_code TEXT,
            customer_name TEXT,
            amount REAL,
            date_created TEXT,
            items TEXT,
            status TEXT DEFAULT 'active',
            total_sp REAL DEFAULT 0.0
        )
    ''')
    
    # Try adding status column if it doesn't exist
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass
    # Try adding total_sp column if it doesn't exist
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN total_sp REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN is_dispatched INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN remark TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

# Initialize the database table if it doesn't exist
init_db()

@invoice_api.route('/api/invoice/create', methods=['POST'])
def create_invoice():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    invoice_no = data.get('invoiceNo', '')
    ds_code = data.get('dsCode', '')
    customer_name = data.get('billedTo', '')
    
    # Parse grandTotal which might have currency symbols, e.g. "₹1,468.23"
    amount_str = str(data.get('grandTotal', '0')).replace('₹', '').replace(',', '').strip()
    import json
    from app import get_db, update_inventory_formulas
    
    try:
        amount = float(amount_str)
    except:
        amount = 0.0
        
    try:
        sp_str = str(data.get('grandTotalSP', '0')).replace('₹', '').replace(',', '').strip()
        total_sp = float(sp_str)
    except:
        total_sp = 0.0
        
    date_created = data.get('date') or datetime.datetime.now().isoformat()
    items = data.get('items', [])
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 0. Check for duplicate invoice_no
        if invoice_no:
            c.execute('SELECT id FROM invoices WHERE invoice_no = ?', (invoice_no,))
            if c.fetchone():
                return jsonify({'error': f'Invoice number {invoice_no} already exists!'}), 400
                
        # 1. Save the invoice
        c.execute(
            'INSERT INTO invoices (invoice_no, ds_code, customer_name, amount, date_created, items, total_sp) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (invoice_no, ds_code, customer_name, amount, date_created, json.dumps(items), total_sp)
        )
        invoice_id = c.lastrowid
        
        # 2. Deduct from inventory (Add to Sold Qty)
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        
        # Find the appropriate 'Sold Qty' column based on invoice date
        sold_qty_col_idx = get_sold_qty_col_idx(all_headers, date_created)
                
        if sold_qty_col_idx:
            for item in items:
                desc = str(item.get('description') or item.get('name') or '').strip()
                qty_sold = float(item.get('qty', 0))
                
                if desc and qty_sold > 0:
                    norm_desc = desc.replace('\n', ' ').replace(' -', '').strip().upper()
                    c.execute(f"SELECT row_num, c3, c{sold_qty_col_idx} FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
                    for inv_row in c.fetchall():
                        c3_val = inv_row['c3'].replace('\n', ' ').replace(' -', '').strip().upper()
                        if c3_val == norm_desc:
                            row_num = inv_row['row_num']
                            current_sold = float(inv_row[2] or 0)
                            new_sold = current_sold + qty_sold
                            
                            c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (new_sold, row_num))
                            update_inventory_formulas(conn, row_num, all_headers)
                            break
        
        # Also update the TOTAL row
        from app import update_totals_row
        update_totals_row(conn)
        
        conn.commit()
        conn.close()
        
        # Automatically submit order to the C&F portal
        if ds_code and items:
            order_type = data.get('orderType', 'sao')
            try:
                from portal_submit_order import submit_order_async
                submit_order_async(ds_code, items, order_type)
            except Exception as ex:
                print("Failed to start portal submission:", ex)
        
        # Trigger background sync to Google Sheets so data survives Render restarts
        try:
            t = threading.Thread(target=init_google_sheets)
            t.daemon = True
            t.start()
        except Exception as e:
            print("Failed to start gsheets sync:", e)

        return jsonify({
            'success': True,
            'message': 'Invoice created successfully (syncing to portal in background)',
            'invoice_id': invoice_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_api.route('/api/invoice/list', methods=['GET'])
def list_invoices():
    from app import get_db
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT c3, c27 FROM inventory WHERE c3 IS NOT NULL")
        sp_map = {}
        for r_inv in c.fetchall():
            k = r_inv['c3']
            v = r_inv['c27']
            if k:
                norm_k = str(k).replace(' -', '').strip().upper()
                try:
                    sp_map[norm_k] = float(str(v or '0').replace(',', '').strip())
                except:
                    pass
                    
        c.execute('SELECT * FROM invoices ORDER BY id DESC')
        rows = c.fetchall()
        
        invoices = []
        for r in rows:
            # sqlite3.Row doesn't have .get(), so we check keys
            keys = r.keys()
            status_val = r['status'] if 'status' in keys else 'active'
            items_json = json.loads(r['items'] or '[]')
            
            db_sp = r['total_sp'] if 'total_sp' in keys else 0.0
            if db_sp == 0.0 and items_json:
                calc_sp = 0.0
                for item in items_json:
                    if 'total_sp' in item:
                        calc_sp += float(str(item.get('total_sp', '0')).replace(',', ''))
                    else:
                        name = str(item.get('name') or item.get('description') or '').replace(' -', '').strip().upper()
                        qty = float(str(item.get('qty', 0)))
                        unit_sp = sp_map.get(name, 0.0)
                        calc_sp += qty * unit_sp
                db_sp = calc_sp
                
            invoices.append({
                'id': r['id'],
                'invoice_no': r['invoice_no'],
                'ds_code': r['ds_code'],
                'customer_name': r['customer_name'],
                'amount': r['amount'],
                'date_created': r['date_created'],
                'status': status_val,
                'items': items_json,
                'grand_total_sp': db_sp,
                'is_dispatched': r['is_dispatched'] if 'is_dispatched' in keys else 0,
                'remark': r['remark'] if 'remark' in keys else ''
            })
            
        conn.close()
        return jsonify({'invoices': invoices})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_api.route('/api/invoice/update/<int:invoice_id>', methods=['POST'])
def update_invoice_info(invoice_id):
    from app import get_db
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        
        if 'is_dispatched' in data:
            val = 1 if data['is_dispatched'] else 0
            c.execute("UPDATE invoices SET is_dispatched = ? WHERE id = ?", (val, invoice_id))
            
        if 'remark' in data:
            c.execute("UPDATE invoices SET remark = ? WHERE id = ?", (data['remark'], invoice_id))
            
        conn.commit()
        conn.close()
        
        # Trigger background sync to Google Sheets
        try:
            from init_gsheets import init_google_sheets
            t = threading.Thread(target=init_google_sheets)
            t.daemon = True
            t.start()
        except Exception as e:
            print("Failed to start gsheets sync:", e)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_api.route('/api/invoice/next_no', methods=['GET'])
def get_next_invoice_no():
    from app import get_db
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT invoice_no FROM invoices ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        conn.close()
        
        if row and row['invoice_no']:
            last_no = row['invoice_no']
            import re
            
            # Match formats like DSR/000067/26-27
            match_dsr = re.search(r'(DSR/)(\d+)(/.*)', last_no)
            if match_dsr:
                prefix = match_dsr.group(1)
                num_str = match_dsr.group(2)
                suffix = match_dsr.group(3)
                next_num = int(num_str) + 1
                next_no = f"{prefix}{str(next_num).zfill(len(num_str))}{suffix}"
                return jsonify({'next_no': next_no})
                
            # Fallback for formats ending in digits
            match = re.search(r'(\d+)$', last_no)
            if match:
                num_str = match.group(1)
                next_num = int(num_str) + 1
                next_no = last_no[:match.start()] + str(next_num).zfill(len(num_str))
                return jsonify({'next_no': next_no})
                
        import datetime
        year = datetime.datetime.now().year
        # Default starting point if no previous invoice found
        return jsonify({'next_no': f'DSR/000068/26-27'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_api.route('/api/invoice/cancel/<int:invoice_id>', methods=['POST'])
def cancel_invoice(invoice_id):
    from app import get_db, update_inventory_formulas, update_totals_row
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 1. Get the invoice to know what to put back
        c.execute('SELECT items, date_created FROM invoices WHERE id = ?', (invoice_id,))
        row = c.fetchone()
        if not row:
            return jsonify({'error': 'Invoice not found'}), 404
            
        items = json.loads(row['items'] or '[]')
        
        # 2. Add back to inventory (Subtract from Sold Qty)
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        
        date_created = row['date_created'] if 'date_created' in row.keys() else ''
        sold_qty_col_idx = get_sold_qty_col_idx(all_headers, date_created)
                
        if sold_qty_col_idx:
            for item in items:
                desc = str(item.get('description') or item.get('name') or '').strip()
                qty_sold = float(item.get('qty', 0))
                
                if desc and qty_sold > 0:
                    norm_desc = desc.replace(' -', '').strip().upper()
                    c.execute(f"SELECT row_num, c3, c{sold_qty_col_idx} FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
                    for inv_row in c.fetchall():
                        c3_val = inv_row['c3'].replace(' -', '').strip().upper()
                        if c3_val == norm_desc:
                            row_num = inv_row['row_num']
                            current_sold = float(inv_row[2] or 0)
                            # We subtract because we are cancelling the invoice
                            new_sold = max(0, current_sold - qty_sold)
                            
                            c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (new_sold, row_num))
                            update_inventory_formulas(conn, row_num, all_headers)
                            break
        
        # 3. Update the invoice status to cancelled in the DB
        c.execute("UPDATE invoices SET status = 'cancelled' WHERE id = ?", (invoice_id,))
        
        # 4. Update the TOTAL row
        update_totals_row(conn)
        
        conn.commit()
        conn.close()
        
        # Trigger background sync to Google Sheets
        try:
            t = threading.Thread(target=init_google_sheets)
            t.daemon = True
            t.start()
        except Exception as e:
            print("Failed to start gsheets sync:", e)
        
        return jsonify({'success': True, 'message': 'Invoice cancelled and inventory restored.'}), 200
    except Exception as e:
        print("Error cancelling invoice:", str(e))
        return jsonify({'error': str(e)}), 500
