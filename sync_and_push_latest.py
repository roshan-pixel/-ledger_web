"""
sync_and_push_latest.py
-----------------------
1. Syncs new invoices from Render (DSR/000296/26-27 to DSR/000309/26-27) into local ledger.db.
2. Submits all 14 new invoices (including DSR/000301 and 0C76FE0F DSR/000305) to AWPL portal in parallel.
"""

import requests
import sqlite3
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from fast_bulk_push import (
    login_and_save_session,
    submit_one,
    log,
    SESSION_FILE,
    DB_PATH
)

RENDER_API_URL = 'https://ledger-web-app.onrender.com/api/invoice/list'

def sync_render_invoices_to_local_db():
    log("[SYNC] Fetching live invoices from Render...")
    try:
        res = requests.get(RENDER_API_URL, timeout=35)
        data = res.json()
        invoices = data.get('invoices', [])
        log(f"[SYNC] Retrieved {len(invoices)} invoices from Render.")
    except Exception as e:
        log(f"[SYNC] ❌ Failed to fetch from Render: {e}")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all invoice_no currently in local DB
    cur.execute("SELECT invoice_no FROM invoices")
    existing_nos = set(r['invoice_no'] for r in cur.fetchall())

    inserted_count = 0
    new_invoices = []

    for inv in invoices:
        inv_no = inv.get('invoice_no')
        if not inv_no:
            continue

        # Check if it's one of the new batch (296-309) or missing locally
        if inv_no not in existing_nos:
            items_str = inv.get('items')
            if isinstance(items_str, list):
                items_str = json.dumps(items_str)
            elif not items_str:
                items_str = '[]'

            cur.execute("""
                INSERT INTO invoices (
                    invoice_no, ds_code, customer_name, amount, date_created,
                    items, status, total_sp, is_dispatched, remark, tid,
                    mobile, delivery_date, stock_point
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv_no,
                inv.get('ds_code', ''),
                inv.get('customer_name', ''),
                float(inv.get('amount') or 0),
                inv.get('date_created', ''),
                items_str,
                inv.get('status', 'active'),
                float(inv.get('total_sp') or 0),
                int(inv.get('is_dispatched') or 0),
                inv.get('remark', ''),
                inv.get('tid', ''),
                inv.get('mobile', ''),
                inv.get('delivery_date', ''),
                inv.get('stock_point', '')
            ))
            inserted_count += 1
            log(f"[SYNC] Stored new invoice {inv_no} (DS: {inv.get('ds_code')}, {inv.get('customer_name')})")

        # Parse items for submission if undispatched
        raw_items = inv.get('items') or []
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except:
                raw_items = []

        parsed = [
            {'description': str(it.get('description') or it.get('name') or ''),
             'qty': float(it.get('qty') or it.get('quantity') or 0)}
            for it in raw_items
            if (it.get('description') or it.get('name')) and float(it.get('qty') or 0) > 0
        ]

        # Target batch: invoices >= 296
        # Or any undispatched invoices >= 296
        no_digits = "".join(filter(str.isdigit, inv_no.split('/')[1] if '/' in inv_no else ''))
        try:
            num = int(no_digits)
        except:
            num = 0

        if num >= 296 and parsed:
            inv_dict = dict(inv)
            inv_dict['items_parsed'] = parsed
            new_invoices.append(inv_dict)

    conn.commit()
    conn.close()
    log(f"[SYNC] Inserted {inserted_count} new invoices into local ledger.db.")
    return new_invoices

def main():
    target_invoices = sync_render_invoices_to_local_db()

    log("\n" + "="*65)
    log(f"  TARGET BATCH FOR AWPL PORTAL: {len(target_invoices)} Invoices")
    log("="*65)

    for i, inv in enumerate(target_invoices, 1):
        log(f"  [{i:>2}] {inv['invoice_no']:20s}  DS:{inv['ds_code']:12s}  "
            f"{inv['customer_name']:30s}  {len(inv['items_parsed'])} item(s)  ({inv.get('date_created')})")

    if not target_invoices:
        log("No target invoices found to submit.")
        return

    # Check for DSR/000301 and 0C76FE0F
    has_301 = any('301' in inv['invoice_no'] for inv in target_invoices)
    has_0c76 = any('0C76FE0F' in inv['ds_code'].upper() for inv in target_invoices)
    log(f"\nVerification: DSR/000301 present? {'YES ✅' if has_301 else 'NO ❌'}")
    log(f"Verification: 0C76FE0F (C REMLALFAKAWMI) present? {'YES ✅' if has_0c76 else 'NO ❌'}\n")

    # Step 1: Login once
    if not login_and_save_session():
        log("❌ Login failed. Aborting.")
        return

    # Step 2: Parallel upload with 4 workers
    num_workers = 4
    log(f"Launching {num_workers} parallel workers to push {len(target_invoices)} invoices to AWPL portal...")
    t0 = time.time()
    success_list, fail_list = [], []

    with ThreadPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(submit_one, inv): inv['invoice_no'] for inv in target_invoices}
        done = 0
        for fut in as_completed(futures):
            invoice_no, ok, msg = fut.result()
            done += 1
            if ok:
                success_list.append(invoice_no)
            else:
                fail_list.append((invoice_no, msg))
            log(f"Progress: {done}/{len(target_invoices)} done  |  ✅ {len(success_list)}  ❌ {len(fail_list)}")

    elapsed = time.time() - t0
    log("="*65)
    log(f"DONE in {elapsed:.0f}s  |  ✅ {len(success_list)} succeeded  |  ❌ {len(fail_list)} failed")
    if success_list:
        log("Succeeded:")
        for n in success_list:
            log(f"  ✅ {n}")
    if fail_list:
        log("Failed:")
        for n, r in fail_list:
            log(f"  ❌ {n}: {r}")
    log("="*65)

if __name__ == '__main__':
    main()
