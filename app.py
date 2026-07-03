import os
import sqlite3
import json
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
from invoice_api import invoice_api
app.register_blueprint(invoice_api)

DB_PATH = 'ledger.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

@app.route('/invoice')
def invoice():
    return render_template('invoice.html')

@app.route('/old_index')
def index():
    return render_template('index.html')

@app.route('/inventory_master')
def inventory_master():
    return render_template('inventory_master.html')

@app.route('/portal_sync')
def portal_sync_page():
    return render_template('portal_sync.html')

@app.route('/api/kpi')
def api_kpi():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Recalculate KPIs based on current inventory
        # Total SKUs
        c.execute("SELECT COUNT(*) FROM inventory WHERE c3 != '' AND c3 IS NOT NULL")
        total_skus = c.fetchone()[0]
        
        # We need to know which columns are what based on headers
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        headers = json.loads(c.fetchone()[0])
        
        # Find indices (1-based)
        dp_idx = None
        rem_qty_idx = None
        rem_val_idx = None
        for i, h in enumerate(headers):
            if h == 'Price/Pc (Rs.)': dp_idx = i + 1
            elif h == 'Remaining Qty': rem_qty_idx = i + 1
            elif h == 'Remaining Value (Rs.)': rem_val_idx = i + 1
            elif h == 'Total Qty': avail_stock_idx = i + 1
            
        if not rem_qty_idx: rem_qty_idx = 19
        if not rem_val_idx: rem_val_idx = 20
        
        c.execute(f"SELECT SUM(CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL)) FROM inventory WHERE c{rem_qty_idx} != ''")
        rem_qty = c.fetchone()[0] or 0
        
        c.execute(f"SELECT SUM(CAST(REPLACE(c{rem_val_idx}, ',', '') AS REAL)) FROM inventory WHERE c{rem_val_idx} != ''")
        rem_val = c.fetchone()[0] or 0
        
        c.execute(f"SELECT COUNT(*) FROM inventory WHERE CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) <= 10 AND c{rem_qty_idx} != ''")
        low_stock = c.fetchone()[0] or 0
        
        # Read other static KPIs from DB
        c.execute("SELECT key, value FROM kpis")
        kpis = {row['key']: row['value'] for row in c.fetchall()}
        
        # Overwrite dynamic ones
        kpis['Total SKUs'] = str(total_skus)
        kpis['Remaining Qty'] = str(rem_qty)
        kpis['Gross Stock Value'] = str(rem_val)
        kpis['Low Stock counts'] = str(low_stock)
        
        conn.close()
        return jsonify(kpis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/inventory')
def api_inventory():
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        headers_json = c.fetchone()
        if not headers_json:
            return jsonify({"error": "Headers not found"}), 500
            
        all_headers = json.loads(headers_json[0])
        # We only return first 19 columns for inventory view usually, but let's return all non-empty
        # Or just return exactly 19 as before
        headers = all_headers[:19]
        # Replace empty strings with Col_X
        headers = [h if h else f"Col_{i+1}" for i, h in enumerate(headers)]
        
        cols_to_select = [f"c{i}" for i in range(1, 20)]
        c.execute(f"SELECT row_num, {', '.join(cols_to_select)} FROM inventory ORDER BY row_num")
        
        data = []
        for row in c.fetchall():
            if not row['c3']: # Product name empty
                continue
            row_data = {}
            for i, h in enumerate(headers):
                row_data[h] = row[f'c{i+1}']
            row_data['__row'] = row['row_num']
            data.append(row_data)
            
        conn.close()
        return jsonify({"headers": headers, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def update_inventory_formulas(conn, row_num, headers):
    """Recalculate formulas for a row."""
    c = conn.cursor()
    c.execute("SELECT * FROM inventory WHERE row_num=?", (row_num,))
    row = c.fetchone()
    if not row:
        return
        
    try:
        try:
            rem_qty_idx = headers.index('Remaining Qty') + 1
            rem_val_idx = headers.index('Remaining Value (Rs.)') + 1
            # "Total Sold Qty" is not in the array, let's just compute from sold columns
            dp = float(str(row[f'c{headers.index("Price/Pc (Rs.)")+1}' ]).replace(',', '') or 0)
            avail_stock = float(str(row[f'c{headers.index("Total Qty")+1}' ]).replace(',', '') or 0)
        except ValueError:
            rem_qty_idx = 19
            rem_val_idx = 20
            dp = float(str(row['c5']).replace(',', '') or 0)
            avail_stock = float(str(row['c7']).replace(',', '') or 0)
            
        # sum sold qtys
        sold_cols = []
        for i, h in enumerate(headers):
            if str(h).startswith("Sold Qty"):
                sold_cols.append(f"c{i+1}")
                
        total_sold = 0
        for col in sold_cols:
            val = str(row[col]).replace(',', '')
            if val:
                total_sold += float(val)
                
        rem_qty = avail_stock - total_sold
        rem_val = rem_qty * dp
        
        c.execute(f"UPDATE inventory SET c{rem_qty_idx}=?, c{rem_val_idx}=? WHERE row_num=?",
                  (rem_qty, rem_val, row_num))
    except Exception as e:
        print("Error updating formulas:", e)


@app.route('/api/update', methods=['POST'])
def api_update():
    updates = request.json.get('updates', [])
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        header_map = {str(h) if h else f"Col_{i+1}": i+1 for i, h in enumerate(all_headers[:19])}
        
        for update in updates:
            row_num = update['row']
            for k, v in update['changes'].items():
                if k in header_map:
                    col_idx = header_map[k]
                    c.execute(f"UPDATE inventory SET c{col_idx}=? WHERE row_num=?", (str(v), row_num))
            
            update_inventory_formulas(conn, row_num, all_headers)
            
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/portal_sync', methods=['POST'])
def api_portal_sync():
    """Run the portal sync directly to SQLite!"""
    payload   = request.json or {}
    from_date = payload.get('from_date', '')
    to_date   = payload.get('to_date', '')
    if not from_date or not to_date:
        from datetime import datetime
        today     = datetime.now().strftime('%d/%m/%Y')
        from_date = today
        to_date   = today
    try:
        # We need to adapt portal_sync to write to SQLite instead of Excel!
        # For now, if we use the old script it will fail since we moved to SQLite.
        # Let's import the new SQLite version of portal_sync.
        # To save time, we will rewrite the sync endpoint in app_sqlite directly or create portal_sync_sqlite.py
        return jsonify({'error': 'Portal Sync is currently disabled during Cloud Migration.'}), 501
    except Exception as e:
        return jsonify({'error': str(e), 'updated': 0}), 500


@app.route('/api/inventory_master')
def api_inventory_master():
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        headers = [str(h) if h else f'Col_{i+1}' for i, h in enumerate(all_headers[:22])]
        
        cols = [f"c{i}" for i in range(1, 23)]
        c.execute(f"SELECT row_num, {', '.join(cols)} FROM inventory ORDER BY row_num")
        
        rows = []
        for row in c.fetchall():
            if not row['c3']:
                continue
            row_data = {'__row': row['row_num']}
            for i, h in enumerate(headers):
                row_data[h] = row[f'c{i+1}']
            rows.append(row_data)
            
        conn.close()
        return jsonify({'headers': headers, 'data': rows})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory_master/update', methods=['POST'])
def api_inventory_master_update():
    payload = request.json
    row_num  = payload.get('row')
    col_name = payload.get('col')
    value    = payload.get('value')
    if not row_num or not col_name:
        return jsonify({'error': 'row and col are required'}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        
        col_idx = None
        for i, h in enumerate(all_headers[:22]):
            if str(h) == col_name or (not h and col_name == f"Col_{i+1}"):
                col_idx = i + 1
                break
                
        if not col_idx:
            return jsonify({'error': f'Column "{col_name}" not found'}), 404
            
        c.execute(f"UPDATE inventory SET c{col_idx}=? WHERE row_num=?", (str(value), row_num))
        update_inventory_formulas(conn, row_num, all_headers)
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'row': row_num, 'col': col_name, 'value': value})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/customer')
def api_customer():
    ds_code = request.args.get('ds_code', '').strip().upper()
    if not ds_code:
        return jsonify({'error': 'ds_code is required'}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM customers WHERE ds_code=?", (ds_code,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'ds_code':          row['ds_code'],
                'ds_name':          row['ds_name'],
                'mobile':           row['mobile'],
                'address':          row['address'],
                'shipping_address': row['shipping_address'],
                'shipping_mobile':  row['shipping_mobile'],
                'shipping_pincode': row['shipping_pincode'],
                'last_invoice':     row['last_invoice'],
            })
            
        # Not found in DB, look up live in portal
        try:
            from ds_lookup_api import fetch_ds_from_portal
            portal_data = fetch_ds_from_portal(ds_code)
            if portal_data:
                # Add to DB
                conn = get_db()
                c = conn.cursor()
                c.execute('''INSERT INTO customers 
                             (ds_code, ds_name, mobile, address, shipping_address, shipping_mobile, shipping_pincode, last_invoice) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (portal_data['ds_code'], portal_data['ds_name'], portal_data['mobile'], portal_data['address'], 
                           portal_data['shipping_address'], portal_data['shipping_mobile'], portal_data['shipping_pincode'], portal_data['last_invoice']))
                conn.commit()
                conn.close()
                return jsonify(portal_data)
        except Exception as ex:
            print("Portal lookup error:", ex)
            
        return jsonify({'error': 'DS Code not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Cloud-ready configuration
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
