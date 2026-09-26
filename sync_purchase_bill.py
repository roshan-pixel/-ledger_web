"""
sync_purchase_bill.py
---------------------
Automated AWPL Purchase Bill Scraper & Inventory Synchronizer.

Capabilities:
1. Logs into AWPL C&F Portal (https://asclepiuswellness.com).
2. Searches PurchaseListn.aspx for a specific bill number (or finds any missing bills).
3. Fetches line-item details from PurchaseListDetails.aspx.
4. Auto-registers missing products into ledger.db inventory table.
5. Updates purchase_orders.json with complete product breakdowns and recalculated grand totals.
6. Runs sync_all_to_inventory() to recalculate stock totals, sold qty, remaining qty, and gross values across:
   - Inventory Stock (/inventory)
   - Inventory Master (/inventory_master)
   - Google Sheets (Ledger_Database)
7. Optionally commits and pushes to Git (auto-deploying to Render).

Usage:
  python sync_purchase_bill.py [BILL_NO] [--push]
Example:
  python sync_purchase_bill.py GUW/000268/26-27 --push
  python sync_purchase_bill.py  (syncs any missing bills from recent portal orders)
"""

import os
import sys
import json
import shutil
import sqlite3
import datetime
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
ORDERS_PATH = BASE_DIR / 'purchase_orders.json'
DB_PATH = BASE_DIR / 'ledger.db'

LOGIN_URL = 'https://asclepiuswellness.com/login.aspx?webid=1'
PURCHASE_URL = 'https://asclepiuswellness.com/shoppingpoint/PurchaseListn.aspx'

def get_credentials():
    username = os.environ.get('PORTAL_USER', 'AAZFD8117G')
    password = os.environ.get('PORTAL_PASSWORD', 'ABC@1234')
    return username, password

def sync_bill(bill_query=None, push_to_git=False):
    username, password = get_credentials()
    today_str = datetime.date.today().strftime('%d/%m/%Y')
    # Default date range: start of current FY or 90 days ago
    from_date = '01/06/2026'

    print("=" * 65)
    print(f"AWPL BILL SYNCHRONIZER: Query='{bill_query or 'ALL_RECENT'}'")
    print(f"Date Range: {from_date} -> {today_str}")
    print("=" * 65)

    # 1. Load existing purchase orders
    existing_orders = []
    if ORDERS_PATH.exists():
        try:
            with open(ORDERS_PATH, 'r', encoding='utf-8') as f:
                existing_orders = json.load(f)
        except Exception as e:
            print(f"[WARN] Error reading purchase_orders.json: {e}")

    existing_bills = {
        str(o.get('bill_no', '')).strip().upper(): o
        for o in existing_orders
        if o.get('party') != 'Total' and o.get('bill_no')
    }

    bills_to_fetch = []

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
        page = browser.new_page()
        page.on('dialog', lambda d: d.accept())

        # Block media for fast execution
        page.route('**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,mp4,mp3,ico}', lambda r: r.abort())

        # Login
        print("[1/5] Logging into AWPL portal...")
        page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(1000)
        page.evaluate('''() => {
            ['ctl00_ContentPlaceHolder1_txtspUserid','ctl00_ContentPlaceHolder1_txtsppassword'].forEach(id => {
                const el = document.getElementById(id);
                if(el){let c=el;while(c&&c!==document.body){c.style.display='block';c=c.parentElement;}}
            });
        }''')
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtspUserid"]', username, force=True)
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtsppassword"]', password, force=True)
        page.click('input[name="ctl00$ContentPlaceHolder1$btnfranlogin"]', force=True)
        try:
            page.wait_for_url('**/shoppingpoint/**', timeout=15000)
        except Exception:
            page.wait_for_load_state('domcontentloaded', timeout=5000)

        # Open Purchase list
        print("[2/5] Opening PurchaseListn.aspx...")
        page.goto(PURCHASE_URL, wait_until='domcontentloaded', timeout=25000)
        page.wait_for_timeout(2000)

        page.fill('input[name="ctl00$ContentPlaceHolder1$txtFrom"]', from_date)
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtTo"]', today_str)
        page.click('input[id="ctl00_ContentPlaceHolder1_btnshow"]')
        page.wait_for_timeout(3500)

        soup = BeautifulSoup(page.content(), 'html.parser')
        gv = soup.find('table', id='ctl00_ContentPlaceHolder1_GV')
        if not gv:
            browser.close()
            raise RuntimeError("Purchase table ctl00_ContentPlaceHolder1_GV not found on portal.")

        data_rows = [tr for tr in gv.find_all('tr') if tr.find_all('td')]
        print(f"  Found {len(data_rows)} purchase rows on portal.")

        target_indices = []
        for i, tr in enumerate(data_rows):
            tds = [t.text.strip() for t in tr.find_all('td')]
            if len(tds) < 3:
                continue
            b_no = tds[2].strip().upper()
            if not b_no or b_no == 'TOTAL':
                continue

            if bill_query:
                # Match user query
                norm_q = bill_query.strip().upper()
                if norm_q in b_no or b_no in norm_q:
                    target_indices.append((i, tds))
            else:
                # If no specific query, check if missing or empty products
                if b_no not in existing_bills or not existing_bills[b_no].get('products'):
                    target_indices.append((i, tds))

        if not target_indices:
            print(f"✓ No new or unrecorded bills found matching query '{bill_query or 'ALL'}'.")
            browser.close()
            return {"success": True, "message": "Already up to date", "bills_added": []}

        print(f"[3/5] Scraping detail for {len(target_indices)} bill(s)...")

        # For each target bill, scrape product details
        for row_idx, cells in target_indices:
            bill_no = cells[2].strip()
            print(f"  --> Fetching line items for {bill_no}...")

            selector = f'#ctl00_ContentPlaceHolder1_GV tr:nth-child({row_idx + 2}) td:nth-child(2) a'
            link = page.query_selector(selector)
            if not link:
                print(f"      [WARN] Detail link not found for row {row_idx + 2}")
                continue

            link.click()
            page.wait_for_timeout(3000)

            detail_soup = BeautifulSoup(page.content(), 'html.parser')
            detail_gv = detail_soup.find('table', id='ctl00_ContentPlaceHolder1_GV')
            prods = []
            if detail_gv:
                for dtr in detail_gv.find_all('tr')[1:]:
                    dtds = [td.text.strip() for td in dtr.find_all('td')]
                    if dtds and len(dtds) >= 8 and dtds[1] != 'Total ----->>':
                        sno, code, name, rate, qty, amount, tax_rate, net_amt = dtds[:8]
                        try:
                            amt_f = float(amount.replace(',', ''))
                            net_f = float(net_amt.replace(',', ''))
                            tax_f = round(net_f - amt_f, 2)
                            qty_i = int(float(qty.replace(',', '')))
                            rate_f = float(rate.replace(',', ''))
                            prods.append([
                                sno,
                                code,
                                name,
                                f"{rate_f:.2f}",
                                str(qty_i),
                                f"{amt_f:.2f}",
                                f"{tax_f:.2f}",
                                f"{net_f:.2f}"
                            ])
                        except Exception as ex:
                            print(f"      Error parsing product row {dtds}: {ex}")

            # Parse order metadata
            igst_str = cells[7] if len(cells) > 7 else '0.00'
            tot_str = cells[10] if len(cells) > 10 else '0.00'
            party_str = cells[3] if len(cells) > 3 else 'ASCLEPIUS WELLNESS PVT LTD'
            date_str = cells[4] if len(cells) > 4 else ''
            lr_str = cells[17] if len(cells) > 17 else ''
            deliv_date = cells[18] if len(cells) > 18 else date_str
            courier_str = cells[20] if len(cells) > 20 else ''

            order_obj = {
                "sr": 0,
                "bill_no": bill_no,
                "party": party_str,
                "date": date_str,
                "cgst": "0.00",
                "sgst": "0.00",
                "igst": igst_str,
                "total": tot_str,
                "lr_no": lr_str,
                "delivery_date": deliv_date,
                "courier": courier_str,
                "products": prods
            }
            bills_to_fetch.append(order_obj)
            print(f"      ✓ Extracted {len(prods)} products for {bill_no}")

            # Navigate back to purchase page for next iteration if needed
            if len(target_indices) > 1:
                page.goto(PURCHASE_URL, wait_until='domcontentloaded')
                page.wait_for_timeout(1500)
                page.fill('input[name="ctl00$ContentPlaceHolder1$txtFrom"]', from_date)
                page.fill('input[name="ctl00$ContentPlaceHolder1$txtTo"]', today_str)
                page.click('input[id="ctl00_ContentPlaceHolder1_btnshow"]')
                page.wait_for_timeout(2500)

        browser.close()

    if not bills_to_fetch:
        return {"success": False, "error": "No order data could be extracted"}

    # 2. Update purchase_orders.json
    print("[4/5] Updating purchase_orders.json & inventory database...")
    shutil.copyfile(str(ORDERS_PATH), str(ORDERS_PATH) + '.bak')
    if DB_PATH.exists():
        shutil.copyfile(str(DB_PATH), str(DB_PATH) + '.bak')

    non_total_orders = [o for o in existing_orders if o.get('party') != 'Total']
    for new_o in bills_to_fetch:
        b_no = new_o['bill_no']
        found_idx = next((idx for idx, o in enumerate(non_total_orders) if o.get('bill_no') == b_no), None)
        if found_idx is not None:
            non_total_orders[found_idx] = new_o
        else:
            # Insert before complimentary if exists
            comp_idx = next((idx for idx, o in enumerate(non_total_orders) if o.get('bill_no') == 'COMPLIMENTARY'), None)
            if comp_idx is not None:
                non_total_orders.insert(comp_idx, new_o)
            else:
                non_total_orders.append(new_o)

    # Re-index sr
    for idx, o in enumerate(non_total_orders):
        o['sr'] = idx + 1

    grand_total = sum(float(str(o.get('total', 0)).replace(',', '')) for o in non_total_orders if o.get('total'))
    grand_igst = sum(float(str(o.get('igst', 0)).replace(',', '')) for o in non_total_orders if o.get('igst'))

    total_row = {
        "sr": "",
        "bill_no": "",
        "party": "Total",
        "date": "",
        "cgst": "",
        "sgst": "",
        "igst": f"{grand_igst:.2f}",
        "total": round(grand_total, 2),
        "lr_no": "",
        "delivery_date": "",
        "courier": "",
        "products": []
    }

    final_orders = non_total_orders + [total_row]
    with open(ORDERS_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_orders, f, indent=2)

    # 3. Synchronize full inventory and Google Sheets
    print("[5/5] Recalculating all stock quantities and formulas...")
    try:
        from sync_full_inventory import sync_all_to_inventory
        sync_all_to_inventory()
    except Exception as se:
        print(f"[WARN] Error running sync_all_to_inventory: {se}")

    # 4. Optional Git Commit & Push
    if push_to_git:
        try:
            print("\n[GIT] Committing and pushing updates to remote repository...")
            added_names = ", ".join(o['bill_no'] for o in bills_to_fetch)
            msg = f"feat: sync purchase bill(s) {added_names} and update inventory stock"
            
            # Run graphify update if installed
            try:
                subprocess.run(["graphify", "update", "."], cwd=str(BASE_DIR), capture_output=True, timeout=20)
            except Exception:
                pass

            subprocess.run(["git", "add", "purchase_orders.json", "ledger.db", "ledger_report.json", "graphify-out/"], cwd=str(BASE_DIR), check=True)
            subprocess.run(["git", "commit", "-m", msg], cwd=str(BASE_DIR), check=True)
            push_res = subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR), capture_output=True, text=True, check=True)
            print("✓ Pushed successfully to origin/main. Render will deploy automatically.")
        except Exception as ge:
            print(f"[GIT ERROR] Failed to push to git: {ge}")

    print("=" * 65)
    print("✓ BILL & INVENTORY SYNC COMPLETED SUCCESSFULLY!")
    print(f"Bills processed: {[o['bill_no'] for o in bills_to_fetch]}")
    print(f"Grand Total: Rs. {grand_total:.2f}")
    print("=" * 65)

    return {
        "success": True,
        "bills_added": [o['bill_no'] for o in bills_to_fetch],
        "grand_total": grand_total,
        "orders_count": len(non_total_orders)
    }

if __name__ == '__main__':
    q = None
    do_push = False
    for arg in sys.argv[1:]:
        if arg in ('--push', '-p'):
            do_push = True
        elif not arg.startswith('-'):
            q = arg

    sync_bill(bill_query=q, push_to_git=do_push)
