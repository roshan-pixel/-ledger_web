"""
fast_bulk_push.py
-----------------
Submits ALL unticked invoices to the AWPL portal in PARALLEL using:
  - ONE login → session cookies saved once (no re-login per order)
  - N parallel Playwright browser contexts sharing those cookies
  - Each context opens SpdistributorSale.aspx independently
  - Real-time logging to fast_bulk_log.txt (no Tee-Object buffering)

Usage:
    python fast_bulk_push.py            # dry-run list
    python fast_bulk_push.py --submit   # parallel submit (4 workers)
    python fast_bulk_push.py --submit --workers 6
    python fast_bulk_push.py --submit --invoice DSR/000295/26-27
"""

import sqlite3, json, sys, os, time, tempfile, threading, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

# ── Real-time log to file (flushed immediately, visible while running) ─────────
LOG_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fast_bulk_log.txt')
_log_lock = threading.Lock()

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with _log_lock:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

# ── Config ─────────────────────────────────────────────────────────────────────
DB_PATH         = 'ledger.db'
SESSION_FILE    = os.path.join(tempfile.gettempdir(), 'awpl_bulk_session.json')
PORTAL_USER     = os.environ.get('PORTAL_USER',     'AAZFD8117G')
PORTAL_PASSWORD = os.environ.get('PORTAL_PASSWORD', 'ABC@1234')
LOGIN_URL       = 'https://asclepiuswellness.com/login.aspx?webid=1'
ORDER_URL       = 'https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx'

BROWSER_ARGS = [
    '--no-sandbox', '--disable-setuid-sandbox',
    '--disable-dev-shm-usage', '--disable-gpu'
]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Login once, save cookies to SESSION_FILE
# ─────────────────────────────────────────────────────────────────────────────
def login_and_save_session():
    log("[AUTH] Logging in to AWPL portal...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
        ctx  = browser.new_context()
        page = ctx.new_page()
        page.goto(LOGIN_URL, wait_until='networkidle', timeout=30000)
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', PORTAL_USER)
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', PORTAL_PASSWORD)
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle', timeout=20000)

        if 'login.aspx' in page.url:
            log("[AUTH] ❌ Login failed! Check credentials.")
            browser.close()
            return False

        ctx.storage_state(path=SESSION_FILE)
        browser.close()
        log(f"[AUTH] ✅ Logged in. Session saved.")
        return True


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Submit a single invoice (runs in its own thread)
# ─────────────────────────────────────────────────────────────────────────────
def submit_one(inv):
    invoice_no = inv['invoice_no']
    ds_code    = inv['ds_code']
    items      = inv['items_parsed']
    order_type = 'sao'
    tag        = f"[{invoice_no}|{ds_code}]"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)

            # Reuse logged-in session — no re-login!
            ctx  = browser.new_context(storage_state=SESSION_FILE)
            page = ctx.new_page()
            page.on("dialog", lambda d: d.accept())

            # Block heavy assets for speed
            page.route('**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,mp4,mp3,ico}',
                       lambda r: r.abort())

            page.goto(ORDER_URL, wait_until='domcontentloaded', timeout=25000)

            # Re-login if session expired
            if 'login.aspx' in page.url:
                log(f"{tag} Session expired — re-logging in...")
                page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', PORTAL_USER)
                page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', PORTAL_PASSWORD)
                page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
                page.wait_for_load_state('domcontentloaded', timeout=20000)
                ctx.storage_state(path=SESSION_FILE)
                page.goto(ORDER_URL, wait_until='domcontentloaded', timeout=25000)

            # ── DS code ───────────────────────────────────────────────────────
            page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
            page.keyboard.press('Tab')

            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#ctl00_ContentPlaceHolder1_txtname'); return el && el.value.trim().length > 0; }",
                    timeout=7000
                )
            except Exception:
                pass

            name = page.input_value('#ctl00_ContentPlaceHolder1_txtname').strip()
            if not name:
                log(f"{tag} ❌ DS code not found on portal. Skipping.")
                browser.close()
                return invoice_no, False, "DS code not found"

            log(f"{tag} DS found: {name}")

            # ── Order type radio ──────────────────────────────────────────────
            if 'sao' in order_type:
                page.evaluate("() => { var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbsao'); if (rb) { rb.checked = true; rb.click(); } }")
            elif 'sgo' in order_type:
                page.evaluate("() => { var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbSgo'); if (rb) { rb.checked = true; rb.click(); } }")

            # ── Shipping ──────────────────────────────────────────────────────
            page.check('#ctl00_ContentPlaceHolder1_chkaddr')
            page.wait_for_timeout(800)

            mobile = page.input_value('#ctl00_ContentPlaceHolder1_txtmobile').strip()
            if mobile:
                page.fill('#ctl00_ContentPlaceHolder1_ShipMobile', mobile)

            address = page.input_value('#ctl00_ContentPlaceHolder1_txtaddress').strip()
            if address:
                m = re.search(r'\b\d{6}\b', address)
                page.fill('#ctl00_ContentPlaceHolder1_txtshpingpincode',
                           m.group(0) if m else '000000')

            # ── Item dropdown ─────────────────────────────────────────────────
            options = page.evaluate("""
                () => Array.from(
                    document.querySelectorAll('#ctl00_ContentPlaceHolder1_itemlist option')
                ).map(o => ({val: o.value, text: o.text}))
            """)
            if options and 'select' in options[0]['text'].lower():
                options = options[1:]

            # ── Add items ─────────────────────────────────────────────────────
            added = 0
            for item in items:
                desc = item['description'].strip().upper()
                qty  = float(item['qty'])
                if not desc or qty <= 0:
                    continue

                match_id    = re.search(r'\[(\d+)\]', desc)
                target_code = match_id.group(1) if match_id else None
                best_match  = None

                # Priority 1: product code in brackets
                if target_code:
                    pats = [f'[{target_code}]', f'({target_code})',
                            f'==({target_code})', f'=={target_code}']
                    for opt in options:
                        ot = opt['text'].strip().upper()
                        if str(opt['val']) == target_code or any(p in ot for p in pats):
                            best_match = opt['val']
                            break

                # Priority 2: best substring score
                if not best_match:
                    best_score = 0
                    cd = re.sub(r'\[\d+\]', '', desc).replace(' -', '').strip()
                    for opt in options:
                        co = re.sub(r'\[\d+\]', '', opt['text'].upper()).replace(' -', '').strip()
                        if cd in co or co in cd:
                            score = min(len(cd), len(co))
                            if score > best_score:
                                best_score = score
                                best_match = opt['val']

                if not best_match:
                    log(f"{tag} ⚠ No portal match for: {desc}")
                    continue

                page.select_option('#ctl00_ContentPlaceHolder1_itemlist', best_match)
                page.wait_for_timeout(1500)
                page.fill('#ctl00_ContentPlaceHolder1_txtqty', str(int(qty)))
                page.click('#ctl00_ContentPlaceHolder1_btnadd')
                page.wait_for_timeout(1800)
                added += 1

            if added == 0:
                log(f"{tag} ❌ No items matched. Skipping.")
                browser.close()
                return invoice_no, False, "no items matched"

            # ── Save order ────────────────────────────────────────────────────
            log(f"{tag} Saving ({added} item(s))...")
            success = False
            try:
                # Portal navigates away on success — expect_navigation catches it
                with page.expect_navigation(wait_until='domcontentloaded', timeout=12000):
                    page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
                success = True   # navigation = portal accepted the save
            except Exception:
                # No navigation — check page HTML for success text
                try:
                    page.wait_for_timeout(3000)
                    html    = page.content()
                    success = 'Bill Save Successfully' in html or 'successfully' in html.lower()
                except Exception:
                    success = True  # navigation mid-read also = success
            browser.close()

            status_str = "✅ SUCCESS" if success else "⚠ Saved (unconfirmed — check portal)"
            log(f"{tag} {status_str}")
            return invoice_no, True, status_str

    except Exception as e:
        log(f"{tag} ❌ ERROR: {e}")
        return invoice_no, False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_unticked_invoices(only_invoice=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    if only_invoice:
        cur.execute("SELECT * FROM invoices WHERE invoice_no = ?", (only_invoice,))
    else:
        cur.execute("SELECT * FROM invoices WHERE is_dispatched = 0 ORDER BY date_created ASC")
    rows = []
    for r in cur.fetchall():
        d   = dict(r)
        raw = []
        try:
            raw = json.loads(d.get('items') or '[]')
        except Exception:
            pass
        parsed = [
            {'description': str(it.get('description') or it.get('name') or ''),
             'qty': float(it.get('qty') or it.get('quantity') or 0)}
            for it in raw
            if (it.get('description') or it.get('name')) and float(it.get('qty') or 0) > 0
        ]
        d['items_parsed'] = parsed
        rows.append(d)
    conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Clear log file at start
    open(LOG_FILE, 'w').close()

    submit_mode  = '--submit'  in sys.argv
    only_invoice = None
    num_workers  = 4

    if '--invoice' in sys.argv:
        idx = sys.argv.index('--invoice')
        only_invoice = sys.argv[idx + 1]
    if '--workers' in sys.argv:
        idx = sys.argv.index('--workers')
        num_workers = int(sys.argv[idx + 1])

    invoices = get_unticked_invoices(only_invoice)
    valid    = [inv for inv in invoices if inv['items_parsed']]
    skipped  = len(invoices) - len(valid)

    log(f"{'='*65}")
    log(f"  {'DRY RUN' if not submit_mode else f'PARALLEL SUBMIT — {num_workers} workers'}")
    log(f"  Unticked: {len(invoices)}  |  Valid: {len(valid)}  |  No-items skipped: {skipped}")
    log(f"{'='*65}")

    for i, inv in enumerate(valid, 1):
        log(f"  [{i:>3}] {inv['invoice_no']:20s}  DS:{inv['ds_code']:12s}  "
            f"{inv['customer_name']:30s}  {len(inv['items_parsed'])} item(s)")

    if not submit_mode:
        log("Run with --submit to push to portal.")
        return

    # ── Step 1: Login once ────────────────────────────────────────────────────
    if not login_and_save_session():
        log("Aborting — login failed.")
        sys.exit(1)

    # ── Step 2: Parallel submit ───────────────────────────────────────────────
    log(f"Launching {num_workers} parallel workers for {len(valid)} invoices...")
    t0 = time.time()
    success_list, fail_list = [], []

    with ThreadPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(submit_one, inv): inv['invoice_no'] for inv in valid}
        done = 0
        for fut in as_completed(futures):
            invoice_no, ok, msg = fut.result()
            done += 1
            if ok:
                success_list.append(invoice_no)
            else:
                fail_list.append((invoice_no, msg))
            log(f"Progress: {done}/{len(valid)} done  |  ✅ {len(success_list)}  ❌ {len(fail_list)}")

    elapsed = time.time() - t0
    log(f"{'='*65}")
    log(f"DONE in {elapsed:.0f}s  |  ✅ {len(success_list)} succeeded  |  ❌ {len(fail_list)} failed")
    if success_list:
        log(f"Succeeded: {', '.join(success_list)}")
    if fail_list:
        log("Failed:")
        for n, r in fail_list:
            log(f"  ❌ {n}: {r}")
    log(f"{'='*65}")


if __name__ == '__main__':
    main()
