from flask import Blueprint, request, jsonify
import sqlite3
import datetime
import json


invoice_api = Blueprint('invoice_api', __name__)

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
            items TEXT
        )
    ''')
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
        
    date_created = data.get('date') or datetime.datetime.now().isoformat()
    items = data.get('items', [])
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 1. Save the invoice
        c.execute(
            'INSERT INTO invoices (invoice_no, ds_code, customer_name, amount, date_created, items) VALUES (?, ?, ?, ?, ?, ?)',
            (invoice_no, ds_code, customer_name, amount, date_created, json.dumps(items))
        )
        invoice_id = c.lastrowid
        
        # 2. Deduct from inventory (Add to Sold Qty)
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        
        # Find the first 'Sold Qty' column
        sold_qty_col_idx = None
        for i, h in enumerate(all_headers):
            if str(h).startswith("Sold Qty"):
                sold_qty_col_idx = i + 1
                break
                
        if sold_qty_col_idx:
            for item in items:
                desc = item.get('description', '').strip()
                qty_sold = float(item.get('qty', 0))
                
                if desc and qty_sold > 0:
                    # Find the product in inventory
                    c.execute("SELECT row_num, c{} FROM inventory WHERE c3=?".format(sold_qty_col_idx), (desc,))
                    row = c.fetchone()
                    if row:
                        row_num = row['row_num']
                        current_sold = float(row[1] or 0)
                        new_sold = current_sold + qty_sold
                        
                        # Update the Sold Qty column
                        c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (new_sold, row_num))
                        
                        # Recalculate remaining qty and value
                        update_inventory_formulas(conn, row_num, all_headers)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Invoice created successfully',
            'invoice_id': invoice_id
        }), 201
    except Exception as e:
        print("Error saving invoice:", str(e))
        return jsonify({'error': str(e)}), 500

@invoice_api.route('/api/invoice/list', methods=['GET'])
def list_invoices():
    from app import get_db
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, invoice_no, ds_code, customer_name, amount, date_created, items, status FROM invoices ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        
        invoices = []
        for row in rows:
            invoices.append({
                'id': row['id'],
                'invoice_no': row['invoice_no'],
                'ds_code': row['ds_code'],
                'customer_name': row['customer_name'],
                'amount': row['amount'],
                'date_created': row['date_created'],
                'items': json.loads(row['items'] or '[]'),
                'status': row['status']
            })
        return jsonify({'invoices': invoices}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_api.route('/api/invoice/cancel/<int:invoice_id>', methods=['POST'])
def cancel_invoice(invoice_id):
    from app import get_db, update_inventory_formulas
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Check if already cancelled
        c.execute("SELECT status, items FROM invoices WHERE id=?", (invoice_id,))
        row = c.fetchone()
        if not row:
            return jsonify({'error': 'Invoice not found'}), 404
        if row['status'] == 'cancelled':
            return jsonify({'error': 'Invoice is already cancelled'}), 400
            
        items = json.loads(row['items'] or '[]')
        
        # Mark as cancelled
        c.execute("UPDATE invoices SET status='cancelled' WHERE id=?", (invoice_id,))
        
        # Reverse inventory (Subtract from Sold Qty)
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        
        sold_qty_col_idx = None
        for i, h in enumerate(all_headers):
            if str(h).startswith("Sold Qty"):
                sold_qty_col_idx = i + 1
                break
                
        if sold_qty_col_idx:
            for item in items:
                desc = item.get('description', '').strip()
                qty_sold = float(item.get('qty', 0))
                
                if desc and qty_sold > 0:
                    c.execute("SELECT row_num, c{} FROM inventory WHERE c3=? ".format(sold_qty_col_idx), (desc,))
                    inv_row = c.fetchone()
                    if inv_row:
                        row_num = inv_row['row_num']
                        current_sold = float(inv_row[1] or 0)
                        # Reverse it
                        new_sold = max(0, current_sold - qty_sold)
                        
                        c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (new_sold, row_num))
                        update_inventory_formulas(conn, row_num, all_headers)
                        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Invoice cancelled and inventory restored.'}), 200
    except Exception as e:
        print("Error cancelling invoice:", str(e))
        return jsonify({'error': str(e)}), 500
