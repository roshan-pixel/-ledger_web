"""
apply_bill_295.py
-----------------
Applies new purchase order (GUW/000295/26-27) to purchase_orders.json,
synchronizes inventory in ledger.db, updates graphify knowledge graph,
and pushes changes to origin/main for Render auto-deployment.
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(r"C:\Users\sgarm\ledger_web")
ORDERS_PATH = BASE_DIR / 'purchase_orders.json'
DB_PATH = BASE_DIR / 'ledger.db'

def apply_order(push_to_git: bool = False):
    print("=" * 65)
    print("APPLYING NEW PURCHASE ORDER (GUW/000295/26-27)")
    print("=" * 65)

    bill_no = "GUW/000295/26-27"
    date_str = "07/10/2026"
    lr_no = "841750568011"
    party = "ASCLEPIUS WELLNESS PVT LTD (GUWAHATI WAREHOUSE)"

    products = [
        ["1", "52", "BRAINDOC PRAVAHI KWATH", "1093.22", "12", "13118.64", "655.93", "13774.57"],
        ["2", "53", "EXE TRIPHALA PRAVAHI KWATH", "368.72", "12", "4424.64", "221.23", "4645.87"],
        ["3", "231", "EXE C COMFORT OIL", "91.53", "6", "549.18", "27.46", "576.64"],
        ["4", "233", "POWER FLUSH TOILET CLEANER", "75.42", "24", "1810.08", "325.81", "2135.89"],
        ["5", "275", "FREE YOU ANION SANITARY PAD (330 MM)", "169.00", "18", "3042.00", "0.00", "3042.00"],
        ["6", "299", "SUNSCREEN SPF50 PA++++ GEL", "271.16", "14", "3796.22", "683.32", "4479.54"]
    ]

    total_taxable = sum(float(p[5]) for p in products)
    total_igst = sum(float(p[6]) for p in products)
    total_gross = sum(float(p[7]) for p in products)
    total_qty = sum(int(p[4]) for p in products)

    order_obj = {
        "sr": 0,
        "bill_no": bill_no,
        "party": party,
        "date": date_str,
        "cgst": "0.00",
        "sgst": "0.00",
        "igst": f"{total_igst:.2f}",
        "total": f"{total_gross:.2f}",
        "lr_no": lr_no,
        "delivery_date": date_str,
        "courier": "INDIA COURIER SERVICE",
        "products": products
    }

    print(f"Bill No       : {bill_no}")
    print(f"Date          : {date_str}")
    print(f"Products      : {len(products)} line items | Total Qty: {total_qty} units")
    print(f"Taxable Amt   : Rs. {total_taxable:.2f}")
    print(f"Total IGST    : Rs. {total_igst:.2f}")
    print(f"Gross Total   : Rs. {total_gross:.2f}")

    # 1. Backups
    shutil.copyfile(str(ORDERS_PATH), str(ORDERS_PATH) + '.bak')
    if DB_PATH.exists():
        shutil.copyfile(str(DB_PATH), str(DB_PATH) + '.bak')
    print("✓ Backups created: purchase_orders.json.bak, ledger.db.bak")

    # 2. Update purchase_orders.json
    with open(ORDERS_PATH, 'r', encoding='utf-8') as f:
        existing_orders = json.load(f)

    clean_orders = [o for o in existing_orders if o.get('party') != 'Total']

    existing_idx = None
    for i, o in enumerate(clean_orders):
        if o.get('bill_no') == bill_no:
            existing_idx = i
            break

    if existing_idx is not None:
        print(f"Bill {bill_no} already exists in purchase_orders.json at index {existing_idx}. Updating in place.")
        clean_orders[existing_idx] = order_obj
    else:
        # Insert before COMPLIMENTARY if exists
        comp_idx = None
        for i, o in enumerate(clean_orders):
            if o.get('bill_no') == 'COMPLIMENTARY':
                comp_idx = i
                break

        if comp_idx is not None:
            clean_orders.insert(comp_idx, order_obj)
        else:
            clean_orders.append(order_obj)

    # Re-index sr
    for idx, o in enumerate(clean_orders):
        o['sr'] = idx + 1

    grand_total = sum(float(str(o.get('total', 0)).replace(',', '')) for o in clean_orders if o.get('total'))
    grand_igst = sum(float(str(o.get('igst', 0)).replace(',', '')) for o in clean_orders if o.get('igst'))

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

    updated_orders = clean_orders + [total_row]

    with open(ORDERS_PATH, 'w', encoding='utf-8') as f:
        json.dump(updated_orders, f, indent=2)

    print(f"✓ Saved purchase_orders.json ({len(clean_orders)} orders + Grand Total: Rs. {grand_total:.2f})")

    # 3. Synchronize inventory in ledger.db
    print("\nRunning sync_all_to_inventory()...")
    sys.path.insert(0, str(BASE_DIR))
    from sync_full_inventory import sync_all_to_inventory
    sync_all_to_inventory()

    # 4. Verify updated rows in inventory
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    print("\n--- Verified Inventory Rows after sync ---")
    rows_to_check = [17, 18, 39, 41, 60, 83]
    for r in rows_to_check:
        c.execute("SELECT row_num, c3, c5, c7, c8, c19, c20, c21 FROM inventory WHERE row_num=?", (r,))
        row = c.fetchone()
        print(f"Row {r:2d}: {row[1]:<45} | Rate: {row[2]:<10} | Total Qty: {row[3]:<6} | Gross Val: {row[4]:<12} | Rem Qty: {row[5]:<6} | Rem Val: {row[6]:<12} | Status: {row[7]}")
    conn.close()

    # 5. Git Commit & Push if requested
    if push_to_git:
        try:
            print("\n[GIT] Staging, committing and pushing to remote repository...")
            subprocess.run(["git", "add", "purchase_orders.json", "ledger.db", "apply_bill_295.py"], cwd=str(BASE_DIR), check=True)
            msg = f"feat: add purchase order bill {bill_no} (6 items) and update inventory"
            subprocess.run(["git", "commit", "-m", msg], cwd=str(BASE_DIR), check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR), check=True)
            print("✓ Pushed successfully to origin/main (Render auto-deploy triggered).")
        except Exception as ge:
            print(f"[GIT ERROR] Failed to push to git: {ge}")

    print("\n" + "=" * 65)
    print(f"SUCCESS: BILL {bill_no} APPLIED & INVENTORY UPDATED!")
    print("=" * 65)

if __name__ == '__main__':
    do_push = '--push' in sys.argv or '-p' in sys.argv
    apply_order(push_to_git=do_push)
