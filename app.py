import os
import sqlite3
import json
import threading
from pathlib import Path
from flask import Flask, jsonify, request, render_template

# Import Google Sheets Sync functions
from restore_gsheets import restore_from_gsheets
from init_gsheets import init_google_sheets

app = Flask(__name__)

from invoice_api import invoice_api
app.register_blueprint(invoice_api)

# Run sync on startup (only if credentials exist, e.g. on Render or local with key)
if os.path.exists('credentials.json') or os.path.exists('/etc/secrets/credentials.json'):
    print("Starting initial sync from Google Sheets...")
    restore_from_gsheets()

DB_PATH = 'ledger.db'

# ---------------------------------------------------------------------------
# Disease Guide – in-memory cache
# ---------------------------------------------------------------------------
_DISEASE_CACHE = None          # list of dicts (flattened, all fields)
_DISEASE_CACHE_LOCK = threading.Lock()

# Fields returned in the list endpoint (heavy ingredient lists excluded)
_LIST_FIELDS = {
    'id', 'disease_name', 'category_name',
    'final_recommended_products', 'recommended_wellness_products',
    'diet', 'exercise', 'ayurvedic_tip', 'things_to_avoid', 'disclaimer',
}

DISEASE_JSON_PATH = Path(__file__).parent / 'static' / 'master_review_data_perfected.json'


def _load_disease_cache():
    """Load and flatten the disease JSON into the module-level cache.
    Thread-safe; reads the file only once per process lifetime."""
    global _DISEASE_CACHE
    with _DISEASE_CACHE_LOCK:
        if _DISEASE_CACHE is not None:
            return _DISEASE_CACHE
        with open(DISEASE_JSON_PATH, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        flat = []
        for category_name, diseases in raw.items():
            for disease in diseases:
                entry = dict(disease)          # shallow copy
                entry['category_name'] = category_name
                entry['id'] = len(flat)        # Store backend index permanently
                flat.append(entry)
        _DISEASE_CACHE = flat
        return _DISEASE_CACHE


@app.route('/api/disease_guide')
def api_disease_guide():
    """Return a lightweight list of diseases, optionally filtered.

    Query params:
      ?q=<term>         – case-insensitive search on disease_name
      ?category=<name>  – exact-match (case-insensitive) on category_name
    """
    try:
        diseases = _load_disease_cache()

        q        = (request.args.get('q', '') or '').strip().lower()
        category = (request.args.get('category', '') or '').strip().lower()

        results = diseases
        if q:
            results = [d for d in results
                       if q in (d.get('disease_name') or '').lower()]
        if category:
            results = [d for d in results
                       if (d.get('category_name') or '').lower() == category]

        # Strip heavy fields – return only _LIST_FIELDS
        slim = [{k: v for k, v in d.items() if k in _LIST_FIELDS}
                for d in results]

        categories = sorted({d.get('category_name', '') for d in diseases})

        return jsonify({'categories': categories, 'diseases': slim, 'total': len(slim)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/disease_guide/<int:idx>')
def api_disease_guide_detail(idx):
    """Return the full record for a single disease by its 0-based index
    in the flattened list (stable within a process lifetime)."""
    try:
        diseases = _load_disease_cache()
        if idx < 0 or idx >= len(diseases):
            return jsonify({'error': 'Index out of range'}), 404
        return jsonify(diseases[idx])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/invoice_history')
def invoice_history():
    return render_template('invoice_history.html')

@app.route('/old_index')
def index():
    return render_template('index.html')

@app.route('/inventory_master')
def inventory_master():
    return render_template('inventory_master.html')

@app.route('/portal_sync')
def portal_sync_page():
    return render_template('portal_sync.html')

@app.route('/disease_guide')
def disease_guide():
    return render_template('disease_guide.html')

@app.route('/mizoram_bronze')
def mizoram_bronze():
    return render_template('mizoram_bronze.html')

@app.route('/api/mizoram_bronze')
def api_mizoram_bronze():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM mizoram_bronze')
        data = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify(data)
    except Exception as e:
        # If table doesn't exist, we can just return empty array so frontend doesn't crash
        if "no such table" in str(e).lower():
            return jsonify([])
        return jsonify({"error": str(e)}), 500

import subprocess
@app.route('/api/fix_historical_buckets', methods=['POST'])
def api_fix_historical_buckets():
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'fix_buckets.py')
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        return jsonify({"success": True, "output": result.stdout, "error": result.stderr})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mizoram_bronze/update', methods=['POST'])
def api_mizoram_bronze_update():
    try:
        data = request.get_json()
        row_id = data.get('id')
        field  = data.get('field')
        value  = data.get('value', '').strip()
        allowed = ['ds_name','mizoram_bronze_date','bronze_achieved','silver_achieved',
                   'silver_update_date','gold_achieved','gold_update_date',
                   'platinum_achieved','platinum_update_date','phone_no']
        if field not in allowed:
            return jsonify({'error': 'Field not allowed'}), 400
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE mizoram_bronze SET {}=? WHERE id=?'.format(field), (value, row_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

from sync_mizoram import sync_mizoram_data
@app.route('/api/sync_mizoram_now', methods=['POST'])
def api_sync_mizoram_now():
    success = sync_mizoram_data()
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Sync failed, check server logs"}), 500

@app.route('/api/kpi')
def api_kpi():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Recalculate KPIs based on current inventory
        # Total SKUs
        c.execute("SELECT COUNT(*) FROM inventory WHERE c3 != '' AND c3 IS NOT NULL AND UPPER(c3) != 'TOTAL'")
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
        
        c.execute(f"SELECT SUM(CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL)) FROM inventory WHERE c{rem_qty_idx} != '' AND UPPER(c3) != 'TOTAL'")
        rem_qty = c.fetchone()[0] or 0
        
        c.execute(f"SELECT SUM(CAST(REPLACE(c{rem_val_idx}, ',', '') AS REAL)) FROM inventory WHERE c{rem_val_idx} != '' AND UPPER(c3) != 'TOTAL'")
        # We will override rem_val below to ensure it perfectly matches Gross - Sales
        
        # Calculate Gross Stock Value using c8 (Gross Value Rs.)
        c.execute(f"SELECT SUM(CAST(REPLACE(c8, ',', '') AS REAL)) FROM inventory WHERE c8 != '' AND UPPER(c3) != 'TOTAL'")
        gross_val = c.fetchone()[0] or 0
        
        c.execute(f"SELECT COUNT(*) FROM inventory WHERE CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) <= 10 AND CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) > 0 AND c{rem_qty_idx} != '' AND UPPER(c3) != 'TOTAL'")
        low_stock = c.fetchone()[0] or 0
        
        c.execute(f"SELECT COUNT(*) FROM inventory WHERE CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) <= 0 AND c{rem_qty_idx} != '' AND UPPER(c3) != 'TOTAL'")
        out_of_stock = c.fetchone()[0] or 0
        
        # Calculate Monthly Sales Value and Week Sales Value directly from the invoices table
        c.execute("SELECT date_created, amount FROM invoices WHERE status != 'cancelled'")
        monthly_sales = 0
        week_sales = 0
        import datetime
        now = datetime.datetime.now()
        
        for r in c.fetchall():
            d_str = r[0]
            amt = r[1] or 0
            monthly_sales += amt
            
            try:
                if '/' in d_str:
                    dt = datetime.datetime.strptime(d_str, '%d/%m/%Y')
                else:
                    dt = datetime.datetime.strptime(d_str, '%Y-%m-%d')
                    
                if (now - dt).days <= 7:
                    week_sales += amt
            except Exception:
                pass
                
        # To ensure the dashboard is mathematically consistent for the user:
        # Remaining Value should equal Gross Stock Value - Monthly Sales Value
        rem_val = gross_val - monthly_sales
        if rem_val < 0: 
            rem_val = 0
        
        # Read other static KPIs from DB
        c.execute("SELECT key, value FROM kpis")
        kpis = {row['key']: row['value'] for row in c.fetchall()}
        
        # Overwrite dynamic ones
        kpis['Total SKUs'] = str(total_skus)
        kpis['Remaining Qty'] = str(rem_qty)
        kpis['Gross Stock Value'] = str(gross_val)
        kpis['Remaining Value'] = str(rem_val)
        kpis['Low Stock Count'] = str(low_stock)
        kpis['Out of Stock Count'] = str(out_of_stock)
        kpis['Monthly Sales Value'] = str(monthly_sales)
        kpis['Week Sales Value'] = str(week_sales)
        
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
        
        headers = []
        cols_to_select = []
        for i, h in enumerate(all_headers):
            if h:  # only non-empty headers
                headers.append(h)
                cols_to_select.append(f"c{i+1}")
                
        c.execute(f"SELECT row_num, {', '.join(cols_to_select)} FROM inventory ORDER BY row_num")
        
        data = []
        for row in c.fetchall():
            prod_name = str(row['c3']).strip().upper() if row['c3'] else ''
            if not prod_name or prod_name == 'TOTAL':
                continue
            row_data = {}
            for h, col in zip(headers, cols_to_select):
                val = row[col]
                if isinstance(val, str) and h in ['Product Name', 'Item Name', 'Product']:
                    val = val.replace('\n', ' ')
                row_data[h] = val
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
    if not row or str(row['c3']).upper() == 'TOTAL':
        return
        
    try:
        try:
            dp_idx = headers.index('Price/Pc (Rs.)') + 1
            tot_qty_idx = headers.index('Total Qty') + 1
            gross_val_idx = headers.index('Gross Value (Rs.)') + 1
            rem_qty_idx = headers.index('Remaining Qty') + 1
            rem_val_idx = headers.index('Remaining Value (Rs.)') + 1
        except ValueError:
            dp_idx = 5
            tot_qty_idx = 7
            gross_val_idx = 8
            rem_qty_idx = 19
            rem_val_idx = 20
            
        dp = float(str(row[f'c{dp_idx}']).replace(',', '') or 0)
        avail_stock = float(str(row[f'c{tot_qty_idx}']).replace(',', '') or 0)
        
        # update Gross Value
        gross_val = avail_stock * dp
        c.execute(f"UPDATE inventory SET c{gross_val_idx}=? WHERE row_num=?", (gross_val, row_num))
            
        # sum sold qtys and update sale values
        total_sold = 0
        for i, h in enumerate(headers):
            if str(h).startswith("Sold Qty"):
                qty_col = f"c{i+1}"
                val_col = f"c{i+2}"
                qty = float(str(row[qty_col]).replace(',', '') or 0)
                total_sold += qty
                sale_val = qty * dp
                c.execute(f"UPDATE inventory SET c{i+2}=? WHERE row_num=?", (sale_val, row_num))
                
        rem_qty = avail_stock - total_sold
        rem_val = rem_qty * dp
        
        # Calculate Total SP
        try:
            sp_pc_idx = headers.index('SP/Pc') + 1
            tot_sp_idx = headers.index('Total SP') + 1
            sp_val = row[f'c{sp_pc_idx}']
            sp_pc = float(str(sp_val).replace(',', '') if sp_val not in (None, '', 'None') else 0)
            tot_sp = sp_pc * rem_qty
        except ValueError:
            # If headers not found, fallback to c27 and c28
            sp_val = row['c27']
            sp_pc = float(str(sp_val).replace(',', '') if sp_val not in (None, '', 'None') else 0)
            tot_sp = sp_pc * rem_qty
            tot_sp_idx = 28
            
        c.execute(f"UPDATE inventory SET c{rem_qty_idx}=?, c{rem_val_idx}=?, c{tot_sp_idx}=? WHERE row_num=?",
                  (rem_qty, rem_val, tot_sp, row_num))
    except Exception as e:
        print("Error updating formulas:", e)

def update_totals_row(conn):
    """Recalculate the TOTAL row at the bottom."""
    try:
        c = conn.cursor()
        c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) = 'TOTAL'")
        total_row = c.fetchone()
        if not total_row:
            return
        
        row_id = total_row['row_num']
        
        # Sum columns 6 through 20, and 28 (Total SP)
        sums = {}
        cols_to_sum = list(range(6, 21)) + [28]
        for col_idx in cols_to_sum:
            c.execute(f"SELECT SUM(CAST(REPLACE(c{col_idx}, ',', '') AS REAL)) FROM inventory WHERE UPPER(c3) != 'TOTAL' AND c{col_idx} != ''")
            s = c.fetchone()[0] or 0
            sums[f"c{col_idx}"] = s
            
        # Update the total row
        updates = ", ".join([f"{k}=?" for k in sums.keys()])
        values = list(sums.values()) + [row_id]
        c.execute(f"UPDATE inventory SET {updates} WHERE row_num=?", values)
    except Exception as e:
        print("Error updating totals row:", e)


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
            
        update_totals_row(conn)
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
        
        headers = []
        cols = []
        for i, h in enumerate(all_headers):
            if h:
                headers.append(h)
                cols.append(f"c{i+1}")
        
        c.execute(f"SELECT row_num, {', '.join(cols)} FROM inventory ORDER BY row_num")
        
        rows = []
        for row in c.fetchall():
            if not row['c3']:
                continue
            r = {'__row': row['row_num']}
            for h, col in zip(headers, cols):
                r[h] = row[col]
            rows.append(r)
            
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
        
        update_totals_row(conn)
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
