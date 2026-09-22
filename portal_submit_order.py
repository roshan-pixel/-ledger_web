import os
import sys
import time
import json
import sqlite3
import re
import tempfile
from playwright.sync_api import sync_playwright

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portal_submit.log')
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'awpl_portal_submission_lock.json')
SESSION_FILE = os.path.join(tempfile.gettempdir(), 'awpl_portal_session.json')

def _log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

def _is_pid_alive(pid):
    if not pid:
        return False
    try:
        if os.name == 'nt':
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def get_active_submission():
    """
    Returns dict of currently active submission if any, or None.
    Automatically clears stale locks (> 10 mins or deceased PID).
    """
    if not os.path.exists(LOCK_FILE):
        return None
    try:
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        started_at = data.get('started_at', 0)
        pid = data.get('pid')
        now = time.time()
        
        # If lock is older than 10 minutes (600s), consider stale
        if now - started_at > 600:
            _log(f"[LOCK] Stale submission lock detected (age: {now - started_at:.1f}s). Releasing lock.")
            release_submission_lock()
            return None
            
        # Check if process is still running
        if pid and not _is_pid_alive(pid):
            _log(f"[LOCK] Process PID {pid} is no longer alive. Releasing lock.")
            release_submission_lock()
            return None
            
        data['elapsed_seconds'] = int(now - started_at)
        return data
    except Exception as e:
        _log(f"[LOCK] Error checking lock file: {e}")
        return None

def acquire_submission_lock(invoice_id, invoice_no, ds_code, pid=None, force=False):
    """
    Attempts to acquire the single-submission lock.
    If force=True, overwrites lock for current worker execution.
    Returns (True, lock_data) if acquired, (False, active_data) if already locked.
    """
    if not force:
        active = get_active_submission()
        if active:
            if active.get('pid') == (pid or os.getpid()):
                return True, active
            return False, active
        
    lock_data = {
        'pid': pid or os.getpid(),
        'invoice_id': invoice_id,
        'invoice_no': invoice_no,
        'ds_code': ds_code,
        'started_at': time.time(),
        'status': 'running'
    }
    try:
        with open(LOCK_FILE, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f)
        return True, lock_data
    except Exception as e:
        _log(f"[LOCK] Failed to write lock file: {e}")
        return False, None

def release_submission_lock():
    """Releases the submission lock file."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        _log(f"[LOCK] Error removing lock file: {e}")

def submit_order_to_portal(ds_code, items, order_type='sao', invoice_id=None, invoice_no=None):
    """
    Submits an order to the AWPL C&F portal (SpdistributorSale.aspx) with high performance,
    dynamic postback synchronization, proper shipping address staging, and DB sync.
    Enforces single submission at a time via global lock.
    """
    tag = f"[{invoice_no or ds_code}|{ds_code}]"
    _log(f"{tag} Starting portal submission (type: {order_type}, items: {len(items)}, inv_id: {invoice_id})...")
    
    # Claim lock for current process
    acquire_submission_lock(invoice_id, invoice_no, ds_code, pid=os.getpid(), force=True)
    
    username = os.environ.get('PORTAL_USER', 'AAZFD8117G')
    password = os.environ.get('PORTAL_PASSWORD', 'ABC@1234')

    success = False
    dialog_history = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--disable-extensions'
                ]
            )
            
            # Check if saved browser session is reusable (< 40 mins old)
            session_valid = False
            if os.path.exists(SESSION_FILE):
                try:
                    if time.time() - os.path.getmtime(SESSION_FILE) < 2400:
                        session_valid = True
                except Exception:
                    session_valid = False

            if session_valid:
                try:
                    ctx = browser.new_context(storage_state=SESSION_FILE)
                except Exception:
                    ctx = browser.new_context()
                    session_valid = False
            else:
                ctx = browser.new_context()

            page = ctx.new_page()

            def handle_dialog(dialog):
                _log(f"{tag} [PORTAL DIALOG] {dialog.message} ({dialog.type})")
                dialog_history.append(dialog.message)
                dialog.accept()
            page.on("dialog", handle_dialog)

            # Block heavy media/images/fonts for 5x speedup and lower memory usage
            page.route('**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,mp4,mp3,ico}', lambda r: r.abort())

            # 1. Check or Perform Login
            t0 = time.time()
            logged_in = False
            if session_valid:
                _log(f"{tag} Reusing saved session cookies...")
                try:
                    page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='domcontentloaded', timeout=15000)
                    if 'login.aspx' not in page.url.lower():
                        logged_in = True
                        _log(f"{tag}    Saved session valid! Skipped login step in {time.time()-t0:.2f}s")
                except Exception as se:
                    _log(f"{tag}    Saved session navigation failed ({se}); falling back to full login.")

            if not logged_in:
                _log(f"{tag} 1. Logging in to AWPL portal...")
                t_login = time.time()
                page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='domcontentloaded', timeout=30000)
                page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', username)
                page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', password)
                page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
                try:
                    page.wait_for_url('**/shoppingpoint/**', timeout=25000)
                except Exception:
                    page.wait_for_load_state('domcontentloaded', timeout=10000)
                
                # Save session state for subsequent orders
                try:
                    ctx.storage_state(path=SESSION_FILE)
                except Exception:
                    pass
                _log(f"{tag}    Logged in successfully in {time.time()-t_login:.2f}s")

                # 2. Go to Sales Order page
                _log(f"{tag} 2. Navigating to SpdistributorSale.aspx...")
                t1 = time.time()
                page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='domcontentloaded', timeout=30000)
                _log(f"{tag}    Sale page loaded in {time.time()-t1:.2f}s")

            # 3. Enter DS Code & Wait for Name
            _log(f"{tag} 3. Entering DS Code: {ds_code}...")
            page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
            page.keyboard.press('Tab')

            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#ctl00_ContentPlaceHolder1_txtname'); return el && el.value.trim().length > 0; }",
                    timeout=7000
                )
            except Exception:
                page.wait_for_timeout(2500)

            name = page.input_value('#ctl00_ContentPlaceHolder1_txtname').strip()
            if not name:
                _log(f"{tag} ❌ DS Code '{ds_code}' not found on portal.")
                browser.close()
                return False

            _log(f"{tag}    DS verified: {name}")

            # Radio Button (SAO vs SGO)
            if 'sgo' in str(order_type).lower():
                page.evaluate("() => { var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbSgo'); if (rb) { rb.checked = true; rb.click(); } }")
                _log(f"{tag}    Selected SGO radio")
            else:
                page.evaluate("() => { var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbsao'); if (rb) { rb.checked = true; rb.click(); } }")
                _log(f"{tag}    Selected SAO radio")
            page.wait_for_timeout(500)

            # Check "Same As Profile Address"
            page.check('#ctl00_ContentPlaceHolder1_chkaddr')
            page.wait_for_timeout(600)

            # Read profile mobile and pincode to preserve them
            profile_mobile = page.input_value('#ctl00_ContentPlaceHolder1_txtmobile').strip()
            profile_addr = page.input_value('#ctl00_ContentPlaceHolder1_txtaddress').strip()
            m_pin = re.search(r'\b[1-9]\d{5}\b', profile_addr)
            profile_pin = m_pin.group(0) if m_pin else '796001'

            # 4. Get available products from dropdown
            options = page.evaluate("""() => Array.from(document.querySelectorAll('#ctl00_ContentPlaceHolder1_itemlist option')).map(o => ({val: o.value, text: o.text}))""")
            if options and "select" in options[0]['text'].lower():
                options = options[1:]
            _log(f"{tag}    Total products in portal dropdown: {len(options)}")

            # 5. Add each item with dynamic postback waiting
            _log(f"{tag} 4. Staging {len(items)} items...")
            added_count = 0
            t_items = time.time()

            for idx, item in enumerate(items, 1):
                desc = (item.get('description') or item.get('name') or '').strip().upper()
                try:
                    qty = int(float(str(item.get('qty') or item.get('quantity') or 0)))
                except Exception:
                    qty = 1
                if not desc or qty <= 0:
                    continue

                match_id = re.search(r'\[(\d+)\]', desc)
                target_code = match_id.group(1) if match_id else None
                best_match = None

                # Priority 1: Match product code
                if target_code:
                    code_patterns = [f'[{target_code}]', f'({target_code})', f'==({target_code})', f'=={target_code}']
                    for opt in options:
                        opt_val = str(opt.get('val', '')).strip()
                        opt_text = opt.get('text', '').strip().upper()
                        if opt_val == str(target_code) or any(cp in opt_text for cp in code_patterns):
                            best_match = opt['val']
                            break

                # Priority 2: Substring score
                if not best_match:
                    best_score = 0
                    clean_desc = re.sub(r'\[\d+\]', '', desc).replace(' -', '').strip()
                    for opt in options:
                        opt_text = opt['text'].strip().upper()
                        clean_opt = re.sub(r'\[\d+\]', '', opt_text).replace(' -', '').strip()
                        if clean_desc in clean_opt or clean_opt in clean_desc:
                            score = min(len(clean_desc), len(clean_opt))
                            if score > best_score:
                                best_score = score
                                best_match = opt['val']

                if not best_match:
                    _log(f"{tag} ⚠ No portal match for [{idx}/{len(items)}]: {desc}")
                    continue

                # Count rows before adding to verify postback completion
                prev_rows = page.locator('#ctl00_ContentPlaceHolder1_GridView1 tr').count()

                page.select_option('#ctl00_ContentPlaceHolder1_itemlist', best_match)
                page.wait_for_timeout(350)
                page.fill('#ctl00_ContentPlaceHolder1_txtqty', str(qty))
                page.click('#ctl00_ContentPlaceHolder1_btnadd')

                # Dynamically wait for ASP.NET postback to complete row addition
                try:
                    page.wait_for_function(
                        f"() => (document.querySelectorAll('#ctl00_ContentPlaceHolder1_GridView1 tr').length > {prev_rows})",
                        timeout=4500
                    )
                except Exception:
                    page.wait_for_timeout(1000)

                added_count += 1
                _log(f"{tag}    [{added_count}/{len(items)}] Added [{best_match}]: {desc} x {qty}")

            _log(f"{tag}    Staged {added_count}/{len(items)} items in {time.time()-t_items:.1f}s")

            if added_count == 0:
                _log(f"{tag} ❌ No items were successfully added to the portal grid.")
                browser.close()
                return False

            # 6. Fill Shipping Mobile and Shipping Pincode AFTER all items are added
            # (Ensures item addition postbacks cannot wipe these required fields)
            _log(f"{tag} 5. Filling Shipping Mobile and Pincode...")
            final_mobile = profile_mobile if (profile_mobile and len(profile_mobile) == 10) else '9436386981'
            page.fill('#ctl00_ContentPlaceHolder1_ShipMobile', final_mobile)
            page.fill('#ctl00_ContentPlaceHolder1_txtshpingpincode', profile_pin)
            page.wait_for_timeout(500)

            # 7. Click Save and Verify Dialog
            _log(f"{tag} 6. Saving order...")
            page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
            page.wait_for_timeout(6500)

            success = any(
                "bill save successfully" in str(d).lower() or
                "save successfully" in str(d).lower()
                for d in dialog_history
            )
            if not success and 'Home.aspx' in page.url:
                success = True

            _log(f"{tag} Save completed. Result: {'✅ SUCCESS' if success else '❌ FAILED'}. Dialogs: {dialog_history}")

            # 8. Update DB on Success - Mark portal_saved = 1 (DO NOT TOUCH is_dispatched!)
            if success:
                # Update local SQLite DB
                try:
                    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ledger.db')
                    if os.path.exists(db_path):
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        try:
                            c.execute("ALTER TABLE invoices ADD COLUMN portal_saved INTEGER DEFAULT 0")
                        except Exception:
                            pass

                        if invoice_id:
                            c.execute("UPDATE invoices SET portal_saved = 1 WHERE id = ?", (invoice_id,))
                        elif invoice_no:
                            c.execute("UPDATE invoices SET portal_saved = 1 WHERE invoice_no = ?", (invoice_no,))
                        elif ds_code:
                            c.execute("UPDATE invoices SET portal_saved = 1 WHERE ds_code = ? ORDER BY id DESC LIMIT 1", (ds_code,))
                        conn.commit()
                        conn.close()
                        _log(f"{tag} ✅ Local ledger.db marked as portal_saved = 1 (dispatch status untouched)")
                except Exception as dbe:
                    _log(f"{tag} ❌ Local DB update error: {dbe}")

                # Update Render DB if running externally and invoice_id known
                if invoice_id:
                    try:
                        import requests
                        r = requests.post(
                            f'https://ledger-web-app.onrender.com/api/invoice/update/{invoice_id}',
                            json={'portal_saved': 1, 'password': 'ABC@!234'},
                            timeout=10
                        )
                        _log(f"{tag} Render API response (portal_saved=1): {r.status_code}")
                    except Exception:
                        pass

            browser.close()
            return success

    except Exception as e:
        _log(f"{tag} ❌ Error submitting order to portal: {e}")
        return False
    finally:
        release_submission_lock()


def submit_order_async(ds_code, items, order_type='sao', invoice_id=None, invoice_no=None):
    """
    Launch portal submission as a separate subprocess so it survives Gunicorn's
    worker lifecycle on Render. Output is piped to portal_submit.log.
    Enforces SINGLE SUBMISSION at a time.
    """
    active = get_active_submission()
    if active:
        _log(f"[{invoice_no or ds_code}] ⚠ Cannot launch submission: Already running for {active.get('invoice_no')} (PID {active.get('pid')})")
        return False, f"Submission already in progress for {active.get('invoice_no')}"

    import subprocess
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portal_submit_order.py')
        log_file_handle = open(LOG_FILE, 'a', encoding='utf-8')
        cmd = [
            sys.executable, script_path,
            str(ds_code),
            json.dumps(items),
            str(order_type or 'sao'),
            str(invoice_id or ''),
            str(invoice_no or '')
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=log_file_handle,
            stderr=log_file_handle
        )
        acquire_submission_lock(invoice_id, invoice_no, ds_code, pid=proc.pid, force=True)
        _log(f"[{invoice_no or ds_code}] Portal submission subprocess spawned (PID: {proc.pid}, ID: {invoice_id}).")
        return True, proc.pid
    except Exception as e:
        _log(f"[{invoice_no or ds_code}] ❌ Failed to launch portal subprocess: {e}")
        return False, str(e)


# ── CLI entry-point (called by subprocess.Popen) ─────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: portal_submit_order.py <ds_code> <items_json> [order_type] [invoice_id] [invoice_no]")
        sys.exit(1)

    _ds_code = sys.argv[1]
    _items = json.loads(sys.argv[2])
    _order_type = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else 'sao'
    _inv_id = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
    _inv_no = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None

    _log(f"[SUBPROCESS] Starting submission for DS: {_ds_code}, type: {_order_type}, invoice: {_inv_no} (ID: {_inv_id})")
    ok = submit_order_to_portal(_ds_code, _items, _order_type, invoice_id=_inv_id, invoice_no=_inv_no)
    _log(f"[SUBPROCESS] Submission {'SUCCESS' if ok else 'FAILED'} for {_ds_code} ({_inv_no})")
    sys.exit(0 if ok else 1)
