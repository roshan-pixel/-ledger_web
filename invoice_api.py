from flask import Blueprint, request, jsonify
import os
import sqlite3
import datetime
import json
import threading
import re
from pathlib import Path
from init_gsheets import init_google_sheets

def get_sold_qty_col_idx(all_headers, date_str):
    """Return the column index (1-based) for the Sold Qty column that matches the
    week-bucket of date_str.  Returns None if no Sold Qty columns exist.
    IMPORTANT: only maps the invoice into the Sold Qty columns if the invoice
    month matches the month embedded in the column headers (e.g. 'Jul').  If the
    months differ the invoice belongs to a different monthly block and we return
    None so the caller skips the DB write (inventory_engine handles it
    dynamically instead)."""
    sold_col_headers = []  # list of (col_1based_idx, header_str)
    for i, h in enumerate(all_headers):
        if str(h).startswith("Sold Qty"):
            sold_col_headers.append((i + 1, str(h)))
    if not sold_col_headers:
        return None

    try:
        # Special one-time exemption for 30/06/2026
        if date_str and date_str.startswith('30/06/2026'):
            inv_month_abbr = 'Jun'
            day = 1
        elif 'T' in date_str:
            dt = datetime.datetime.fromisoformat(date_str)
            inv_month_abbr = dt.strftime('%b')  # 'Jul', 'Aug', ...
            day = dt.day
        elif '/' in date_str:
            dt = datetime.datetime.strptime(date_str[:10], '%d/%m/%Y')
            inv_month_abbr = dt.strftime('%b')
            day = dt.day
        else:
            dt = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
            inv_month_abbr = dt.strftime('%b')
            day = dt.day
    except:
        dt = datetime.datetime.now()
        inv_month_abbr = dt.strftime('%b')
        day = dt.day

    # Filter to only the sold-qty columns whose header month matches the invoice month.
    # Header format: "Sold Qty (Jul 1-7)" → second token is month abbr.
    matching_cols = []
    for col_idx, h in sold_col_headers:
        # extract month abbreviation from header, e.g. "Sold Qty (Jul 1-7)" → "Jul"
        import re as _re
        m = _re.search(r'\(([A-Za-z]{3})\s', h)
        if m and m.group(1) == inv_month_abbr:
            matching_cols.append(col_idx)
        elif not m:
            # Header has no month (legacy plain 'Sold Qty') - keep it
            matching_cols.append(col_idx)

    if not matching_cols:
        # Invoice month doesn't match any column month header → skip DB write
        return None

    if day <= 7: week_idx = 0
    elif day <= 14: week_idx = 1
    elif day <= 21: week_idx = 2
    elif day <= 28: week_idx = 3
    else: week_idx = 4

    if week_idx < len(matching_cols):
        return matching_cols[week_idx]
    return matching_cols[-1]


def _get_true_remaining_stock(conn):
    """
    Calculate TRUE remaining stock for every product across ALL months.

    Formula:
        remaining = total_purchased (purchase_orders.json) - cumulative_active_sales (all invoices)

    This is immune to the monthly rollover bug because it does NOT rely on
    the c19 (Remaining Qty) column, which only reflects current-month sold
    quantities after the monthly rollover zeroes them out.

    Returns a dict: { normalized_product_key -> remaining_qty }
    where normalized_product_key = re.sub(r'[^A-Z0-9]', '', product_name.upper())
    """
    import inventory_engine as _ie

    c = conn.cursor()

    # ── 1. Build product-code → norm_key map from inventory table ────────────
    c.execute("SELECT c3 FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
    code_to_normkey = {}
    for row in c.fetchall():
        raw = str(row[0]).strip()
        if not raw or raw.upper() == 'TOTAL':
            continue
        code = _ie.extract_code(raw)
        norm_key = re.sub(r'[^A-Z0-9]', '', raw.upper())
        if code:
            code_to_normkey[code] = norm_key

    # ── 2. Tally purchases from purchase_orders.json ─────────────────────────
    purchased = {}  # norm_key -> total qty
    orders_path = Path(__file__).parent / 'purchase_orders.json'
    if orders_path.exists():
        try:
            with open(orders_path, 'r', encoding='utf-8') as f:
                orders = json.load(f)
            for order in orders:
                for prod in order.get('products', []):
                    if len(prod) < 5:
                        continue
                    code = str(prod[1]).strip()
                    raw_name = str(prod[2]).replace('\n', ' ').strip().upper()
                    try:
                        qty = float(str(prod[4]).replace(',', ''))
                    except Exception:
                        qty = 0
                    if qty <= 0:
                        continue
                    nk = code_to_normkey.get(code) or re.sub(r'[^A-Z0-9]', '', raw_name)
                    purchased[nk] = purchased.get(nk, 0.0) + qty
        except Exception as e:
            print(f"[StockCheck] Warning: could not read purchase_orders.json: {e}")

    # Fallback / manual adjustments: read c7 (Total Qty) directly from inventory
    c.execute("SELECT c3, c7 FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
    for row in c.fetchall():
        raw = str(row[0]).strip()
        if not raw or raw.upper() == 'TOTAL':
            continue
        nk = re.sub(r'[^A-Z0-9]', '', raw.upper())
        try:
            c7_val = float(str(row[1] or '0').replace(',', ''))
        except Exception:
            c7_val = 0.0
        purchased[nk] = max(purchased.get(nk, 0.0), c7_val)

    # ── 3. Tally ALL active invoice sales (across ALL months) ─────────────────
    sold = {}   # norm_key -> total qty sold
    c.execute("SELECT items FROM invoices WHERE status != 'cancelled'")
    for row in c.fetchall():
        try:
            items = json.loads(row[0] or '[]')
        except Exception:
            continue
        for item in items:
            desc = str(item.get('description') or item.get('name') or '').strip()
            if not desc:
                continue
            try:
                qty = float(str(item.get('qty', 0)).replace(',', ''))
            except Exception:
                qty = 0
            if qty <= 0:
                continue
            code = _ie.extract_code(desc)
            nk = code_to_normkey.get(code) if code else None
            if nk is None:
                nk = re.sub(r'[^A-Z0-9]', '', desc.upper())
            sold[nk] = sold.get(nk, 0.0) + qty

    # ── 4. remaining = purchased - sold ──────────────────────────────────────
    remaining = {}
    for nk in set(list(purchased.keys()) + list(sold.keys())):
        remaining[nk] = purchased.get(nk, 0.0) - sold.get(nk, 0.0)

    return remaining


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
def is_complimentary_item(desc):
    if not desc:
        return False
    d = str(desc).strip().upper()
    if 'COMPLIMENTARY' in d or 'COMPLEMENTARY' in d:
        return True
    import re
    if 'HEIGHTDOC' in d or 'HEIGHT DOC' in d or re.search(r'\[494\]|\b494\b', d):
        return True
    if 'THUNDERBLAST' in d or 'THUNDER BLAST' in d or re.search(r'\[41\]|\b41\b', d):
        return True
    return False

init_db()

@invoice_api.route('/api/invoice/create', methods=['POST'])
def create_invoice():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    invoice_no = data.get('invoiceNo', '').strip()
    ds_code = data.get('dsCode', '')
    customer_name = data.get('billedTo', '')
    
    items = data.get('items', [])
    if any(is_complimentary_item(it.get('description') or it.get('name') or '') for it in items):
        if not invoice_no.endswith('*'):
            invoice_no = f"{invoice_no}*"
    
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
        
    # Standardize date to YYYY-MM-DD
    raw_date = data.get('date') or datetime.datetime.now().isoformat()
    raw_date = raw_date.strip()
    date_created = raw_date[:10]  # Take YYYY-MM-DD from YYYY-MM-DDT...
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            date_created = datetime.datetime.strptime(raw_date[:10], fmt).strftime('%Y-%m-%d')
            break
        except ValueError:
            pass

    items = data.get('items', [])
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 0. Check for duplicate invoice_no
        if invoice_no:
            c.execute('SELECT id FROM invoices WHERE invoice_no = ?', (invoice_no,))
            if c.fetchone():
                return jsonify({'error': f'Invoice number {invoice_no} already exists!'}), 400
                
        # 0.5. Validate Stock — STRICT POLICY (true cross-month cumulative check)
        # ─────────────────────────────────────────────────────────────────────
        # BUG FIXED: The old check read the `Remaining Qty` column (c19) from the
        # inventory table. That column is zeroed each month by the monthly rollover,
        # so it only reflected CURRENT-MONTH sales. This allowed invoices to be
        # created when real all-time stock was already 0 or negative.
        #
        # The new check calls _get_true_remaining_stock() which independently
        # computes:  purchased (purchase_orders.json) – sold (ALL active invoices)
        # This is always accurate regardless of which month it is.
        # ─────────────────────────────────────────────────────────────────────
        true_stock = _get_true_remaining_stock(conn)

        # Aggregate requested quantities by normalized product key
        requested_qty = {}
        original_names = {}
        import inventory_engine as _ie
        for item in items:
            desc = str(item.get('description') or item.get('name') or '').strip()
            try:
                qty_req = float(str(item.get('qty', 0)).replace(',', ''))
            except Exception:
                qty_req = 0.0

            if desc and qty_req > 0:
                code = _ie.extract_code(desc)
                # Build code_to_normkey snapshot just for this request
                c.execute("SELECT c3 FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
                code_to_normkey_local = {}
                for r_inv in c.fetchall():
                    raw = str(r_inv[0]).strip()
                    if raw and raw.upper() != 'TOTAL':
                        c2 = _ie.extract_code(raw)
                        if c2:
                            code_to_normkey_local[c2] = re.sub(r'[^A-Z0-9]', '', raw.upper())
                norm_desc = code_to_normkey_local.get(code) if code else None
                if norm_desc is None:
                    norm_desc = re.sub(r'[^A-Z0-9]', '', desc.upper())
                requested_qty[norm_desc] = requested_qty.get(norm_desc, 0.0) + qty_req
                original_names[norm_desc] = desc

        # Check each requested item against the TRUE remaining stock
        for norm_desc, qty_req in requested_qty.items():
            avail = true_stock.get(norm_desc, 0.0)
            if qty_req > avail:
                return jsonify({
                    'error': (
                        f'Strict Policy Error: Not enough stock for '
                        f'{original_names[norm_desc]}. '
                        f'Requested: {int(qty_req)}, '
                        f'Available: {max(0, int(avail))}'
                    )
                }), 400

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
                    # Normalize: strip everything except uppercase alphanumeric
                    norm_desc = re.sub(r'[^A-Z0-9]', '', desc.upper())
                    c.execute(f"SELECT row_num, c3, c{sold_qty_col_idx} FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
                    for inv_row in c.fetchall():
                        # Use SAME normalization on both sides so they can match
                        c3_val = re.sub(r'[^A-Z0-9]', '', str(inv_row['c3']).upper())
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
                submit_order_async(ds_code, items, order_type, invoice_id=invoice_id, invoice_no=invoice_no)
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
        # Sort chronologically by date and numeric invoice number descending
        c.execute('SELECT * FROM invoices ORDER BY date_created DESC, CAST(SUBSTR(invoice_no, 5, 6) AS INTEGER) DESC')
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
                
            has_comp = is_complimentary_item(r['invoice_no']) or any(is_complimentary_item(it.get('description') or it.get('name') or '') for it in items_json)
            inv_no = str(r['invoice_no'] or '').strip()
            if has_comp and not inv_no.endswith('*'):
                inv_no = f"{inv_no}*"

            invoices.append({
                'id': r['id'],
                'invoice_no': inv_no,
                'ds_code': r['ds_code'],
                'customer_name': r['customer_name'],
                'amount': r['amount'],
                'date_created': r['date_created'],
                'status': status_val,
                'items': items_json,
                'grand_total_sp': db_sp,
                'has_complimentary': has_comp,
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
        data = request.get_json() or {}
        conn = get_db()
        c = conn.cursor()
        
        if 'is_dispatched' in data:
            if data.get('password') not in ['ABC!@234', 'ABC@!234']:
                conn.close()
                return jsonify({'error': 'Incorrect password! Authorization required to change dispatched status.'}), 403
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
            last_no = str(row['invoice_no']).rstrip('*').strip()
            import re
            
            # Match formats like DSR/000067/26-27
            match_dsr = re.search(r'(DSR/)(\d+)(/.*)', last_no)
            if match_dsr:
                prefix = match_dsr.group(1)
                num_str = match_dsr.group(2)
                suffix = match_dsr.group(3).rstrip('*')
                next_num = int(num_str) + 1
                next_no = f"{prefix}{str(next_num).zfill(len(num_str))}{suffix}"
                return jsonify({'next_no': next_no})
                
            # Fallback for formats ending in digits
            match = re.search(r'(\d+)$', last_no)
            if match:
                num_str = match.group(1)
                next_num = int(num_str) + 1
                next_no = (last_no[:match.start()] + str(next_num).zfill(len(num_str))).rstrip('*')
                return jsonify({'next_no': next_no})
                
        import datetime
        now = datetime.datetime.now()
        # Financial year: Apr-Mar, e.g. Apr 2026 - Mar 2027 → "26-27"
        fy_start = now.year if now.month >= 4 else now.year - 1
        fy_suffix = f"{str(fy_start)[2:]}-{str(fy_start + 1)[2:]}"
        # Default starting point if no previous invoice found
        return jsonify({'next_no': f'DSR/000001/{fy_suffix}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Set of 65 existing unticked invoice IDs protected from unauthorized cancellation
PROTECTED_UNTICKED_IDS = {
    192, 204, 206, 207, 208, 217, 218, 219, 221, 222, 228, 229, 230, 232, 233,
    234, 235, 236, 239, 240, 242, 243, 244, 245, 249, 250, 251, 252, 253, 254,
    256, 257, 258, 260, 263, 265, 266, 267, 268, 269, 271, 272, 275, 276, 277,
    278, 279, 281, 284, 286, 287, 290, 291, 292, 293, 294, 295, 296, 297, 298,
    299, 300, 301, 302, 303
}

@invoice_api.route('/api/invoice/cancel/<int:invoice_id>', methods=['POST'])
def cancel_invoice(invoice_id):
    from app import get_db, update_inventory_formulas, update_totals_row
    try:
        data = request.get_json(silent=True) or {}
        conn = get_db()
        c = conn.cursor()
        
        # 1. Get the invoice to know what to put back & check dispatch status
        c.execute('SELECT items, date_created, is_dispatched FROM invoices WHERE id = ?', (invoice_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Invoice not found'}), 404
            
        is_dispatched = bool(row['is_dispatched']) if ('is_dispatched' in row.keys() and row['is_dispatched']) else False
        is_protected_unticked = (invoice_id in PROTECTED_UNTICKED_IDS) or (invoice_id <= 303 and not is_dispatched)

        # Password is required ONLY for:
        # 1. These 65 existing unticked invoices
        # 2. Invoices already marked as dispatched
        # New unticked invoices (id > 303) can be cancelled by end users without password
        if is_protected_unticked or is_dispatched:
            pwd = str(data.get('password') or '').strip()
            if pwd not in ['ABC!@234', 'ABC@!234']:
                conn.close()
                reason = "This unticked invoice is protected from cancellation" if is_protected_unticked else "This invoice is marked as dispatched"
                return jsonify({'error': f'Incorrect password! {reason}, authorization password is required.'}), 403
            
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
                    # Use SAME normalization on both sides so they can match
                    norm_desc = re.sub(r'[^A-Z0-9]', '', desc.upper())
                    c.execute(f"SELECT row_num, c3, c{sold_qty_col_idx} FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
                    for inv_row in c.fetchall():
                        c3_val = re.sub(r'[^A-Z0-9]', '', str(inv_row['c3']).upper())
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


@invoice_api.route('/api/portal_order_log', methods=['GET'])
def get_portal_order_log():
    """Returns the last 100 lines of portal_submit.log."""
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portal_submit.log')
    if not os.path.exists(log_file):
        return jsonify({'log': 'No portal submission logs recorded yet.'}), 200
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        return jsonify({'lines': [line.strip() for line in lines[-100:]]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@invoice_api.route('/api/invoice/resubmit/<int:invoice_id>', methods=['POST'])
def resubmit_invoice_to_portal(invoice_id):
    """
    Trigger manual resubmission of an unsaved / undispatched invoice to the AWPL portal.
    """
    from app import get_db
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, invoice_no, ds_code, items, is_dispatched, status FROM invoices WHERE id = ?', (invoice_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return jsonify({'success': False, 'error': f'Invoice ID {invoice_id} not found.'}), 404

        inv_status = row['status'] if 'status' in row.keys() else 'active'
        if inv_status == 'cancelled':
            return jsonify({'success': False, 'error': 'Cannot resubmit a cancelled invoice.'}), 400

        inv_no = row['invoice_no'] or f'INV-{invoice_id}'
        ds_code = row['ds_code']
        raw_items = row['items'] or '[]'
        items = json.loads(raw_items) if isinstance(raw_items, str) else raw_items

        if not ds_code or not items:
            return jsonify({'success': False, 'error': f'Invoice {inv_no} has no DS code or items.'}), 400

        from portal_submit_order import submit_order_async
        submit_order_async(ds_code, items, order_type='sao', invoice_id=invoice_id, invoice_no=inv_no)

        return jsonify({
            'success': True,
            'message': f'Resubmission started in background for {inv_no} (DS: {ds_code})!',
            'invoice_id': invoice_id,
            'invoice_no': inv_no
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


