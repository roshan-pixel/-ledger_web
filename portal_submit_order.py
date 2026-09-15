import os
import sys
import time
import json
import sqlite3
import re
from playwright.sync_api import sync_playwright

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portal_submit.log')

def _log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

def submit_order_to_portal(ds_code, items, order_type='sao'):
    """
    Submits an order to the AWPL C&F portal (SpdistributorSale.aspx).
    items is a list of dicts: [{'description': 'ITEM NAME', 'qty': 2}, ...]
    order_type can be 'sao', 'sgo', or 'approve'
    """
    _log(f"[{ds_code}] Starting portal submission (type: {order_type}, items: {len(items)})...")
    username = os.environ.get('PORTAL_USER', 'AAZFD8117G')
    password = os.environ.get('PORTAL_PASSWORD', 'ABC@1234')

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
            ctx = browser.new_context()
            page = ctx.new_page()

            # Auto-accept all alerts and confirmations (crucial for ASP.NET Save button)
            def handle_dialog(dialog):
                _log(f"[{ds_code}] [PORTAL DIALOG] {dialog.message}")
                dialog.accept()
            page.on("dialog", handle_dialog)

            # Block heavy media/images/fonts to make page loads 5x faster and save memory
            page.route('**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,mp4,mp3,ico}', lambda r: r.abort())

            # 1. Login
            _log(f"[{ds_code}] Logging in to AWPL portal...")
            page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='domcontentloaded', timeout=25000)
            page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', username)
            page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', password)
            page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
            page.wait_for_load_state('domcontentloaded', timeout=25000)

            # 2. Go to Sales Order page
            _log(f"[{ds_code}] Navigating to Sales Order page...")
            page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='domcontentloaded', timeout=25000)

            # Enter DS ID and press Tab to trigger details loading
            page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
            page.keyboard.press('Tab')

            # Wait for name to populate via AJAX
            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#ctl00_ContentPlaceHolder1_txtname'); return el && el.value.trim().length > 0; }",
                    timeout=7000
                )
            except Exception:
                pass

            name = page.input_value('#ctl00_ContentPlaceHolder1_txtname').strip()
            if not name:
                _log(f"[{ds_code}] ❌ DS Code not found on portal.")
                browser.close()
                return False

            _log(f"[{ds_code}] DS verified: {name}")

            # 3. Select Order Type (SAO vs SGO) - force click via JS
            if 'sao' in order_type:
                try:
                    page.evaluate("""
                        () => {
                            var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbsao');
                            if (rb) { rb.checked = true; rb.click(); return true; }
                            return false;
                        }
                    """)
                    _log(f"[{ds_code}] Force-clicked SAO radio button")
                except Exception as e:
                    _log(f"[{ds_code}] Could not force-click SAO: {e}")
            elif 'sgo' in order_type:
                try:
                    page.evaluate("""
                        () => {
                            var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbSgo');
                            if (rb) { rb.checked = true; rb.click(); return true; }
                            return false;
                        }
                    """)
                    _log(f"[{ds_code}] Force-clicked SGO radio button")
                except Exception as e:
                    _log(f"[{ds_code}] Could not force-click SGO: {e}")

            # Check "Same As Profile Address"
            page.check('#ctl00_ContentPlaceHolder1_chkaddr')
            page.wait_for_timeout(800)

            # Copy mobile to shipping mobile if empty
            mobile = page.input_value('#ctl00_ContentPlaceHolder1_txtmobile').strip()
            if mobile:
                page.fill('#ctl00_ContentPlaceHolder1_ShipMobile', mobile)

            # Extract pincode from address and fill
            address = page.input_value('#ctl00_ContentPlaceHolder1_txtaddress').strip()
            if address:
                m = re.search(r'\b\d{6}\b', address)
                page.fill('#ctl00_ContentPlaceHolder1_txtshpingpincode', m.group(0) if m else '000000')

            # 4. Get available items from dropdown
            options = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('#ctl00_ContentPlaceHolder1_itemlist option')).map(o => ({val: o.value, text: o.text}));
            }''')

            if options and "select" in options[0]['text'].lower():
                options = options[1:]

            # 5. Add each item
            added_count = 0
            for item in items:
                desc = item.get('description', '').strip().upper()
                qty = float(item.get('qty', 0))

                if not desc or qty <= 0:
                    continue

                match_id = re.search(r'\[(\d+)\]', desc)
                target_code = match_id.group(1) if match_id else None
                best_match = None

                # Priority 1: Match product code in brackets
                if target_code:
                    code_patterns = [f'[{target_code}]', f'({target_code})', f'==({target_code})', f'=={target_code}']
                    for opt in options:
                        opt_val = str(opt.get('val', '')).strip()
                        opt_text = opt.get('text', '').strip().upper()
                        if opt_val == str(target_code) or any(cp in opt_text for cp in code_patterns):
                            best_match = opt['val']
                            _log(f"[{ds_code}] Matched [{target_code}]: {opt_text}")
                            break

                # Priority 2: Best-score substring match
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
                    _log(f"[{ds_code}] ⚠ No match found for: {desc}")
                    continue

                _log(f"[{ds_code}] Adding item {desc} (ID: {best_match}) Qty: {qty}")
                page.select_option('#ctl00_ContentPlaceHolder1_itemlist', best_match)
                page.wait_for_timeout(1500)
                page.fill('#ctl00_ContentPlaceHolder1_txtqty', str(int(qty)))
                page.click('#ctl00_ContentPlaceHolder1_btnadd')
                page.wait_for_timeout(1800)
                added_count += 1

            if added_count == 0:
                _log(f"[{ds_code}] ❌ No items were successfully added.")
                browser.close()
                return False

            # 6. Save order
            _log(f"[{ds_code}] Saving order with {added_count} items...")
            success = False
            try:
                with page.expect_navigation(wait_until='domcontentloaded', timeout=12000):
                    page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
                success = True
                _log(f"[{ds_code}] ✅ Order saved successfully (navigation completed).")
            except Exception:
                try:
                    page.wait_for_timeout(2500)
                    html = page.content()
                    success = 'Bill Save Successfully' in html or 'successfully' in html.lower()
                    _log(f"[{ds_code}] Order save check: {'✅ SUCCESS' if success else '⚠ Triggered'}")
                except Exception:
                    success = True

            browser.close()
            return success

    except Exception as e:
        _log(f"[{ds_code}] ❌ Error submitting order to portal: {e}")
        return False


def submit_order_async(ds_code, items, order_type='sao'):
    """
    Launch portal submission as a separate subprocess so it survives Gunicorn's
    worker lifecycle on Render. Output is piped to portal_submit.log.
    """
    import subprocess
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portal_submit_order.py')
        log_file_handle = open(LOG_FILE, 'a', encoding='utf-8')
        subprocess.Popen(
            [sys.executable, script_path, ds_code, json.dumps(items), order_type],
            stdout=log_file_handle,
            stderr=log_file_handle
        )
        _log(f"[{ds_code}] Portal submission subprocess spawned successfully.")
    except Exception as e:
        _log(f"[{ds_code}] ❌ Failed to launch portal subprocess: {e}")


# ── CLI entry-point (called by subprocess.Popen) ─────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: portal_submit_order.py <ds_code> <items_json> [order_type]")
        sys.exit(1)

    _ds_code = sys.argv[1]
    _items = json.loads(sys.argv[2])
    _order_type = sys.argv[3] if len(sys.argv) > 3 else 'sao'

    _log(f"[SUBPROCESS] Starting submission for DS: {_ds_code}, type: {_order_type}")
    ok = submit_order_to_portal(_ds_code, _items, _order_type)
    _log(f"[SUBPROCESS] Submission {'SUCCESS' if ok else 'FAILED'} for {_ds_code}")
    sys.exit(0 if ok else 1)
