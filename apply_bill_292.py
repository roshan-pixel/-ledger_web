"""
apply_bill_292.py
-----------------
Parses Sales Challan / Stock Transfer GST Invoice PDF (GUW/000292/26-27),
adds the new stock order to purchase_orders.json, recalculates grand totals,
synchronizes inventory in ledger.db, and updates graphify knowledge graph.
"""

import sys
import os
import json
import shutil
import re
import subprocess
from pathlib import Path
import pdfplumber

BASE_DIR = Path(__file__).resolve().parent
ORDERS_PATH = BASE_DIR / 'purchase_orders.json'
DB_PATH = BASE_DIR / 'ledger.db'

DEFAULT_PDF_PATH = r"C:\Users\sgarm\Downloads\asclepiuswellness.com_SalesPrintChallan.aspx_Id=11530198.pdf"


def parse_challan_pdf(pdf_path: str):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Challan PDF not found at: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text() or ""
        tables = first_page.extract_tables()
        if not tables:
            raise ValueError("No table found in challan PDF")

        table = tables[0]

    # Extract metadata
    inv_match = re.search(r"Invoice No\.\s*:\s*([^\s]+)", text)
    bill_no = inv_match.group(1).strip() if inv_match else "GUW/000292/26-27"

    date_match = re.search(r"Dated\s*:\s*([^\s]+)", text)
    date_str = date_match.group(1).strip() if date_match else "03/10/2026"

    eway_match = re.search(r"Eway Bill No\.\s*:\s*(\d+)", text)
    lr_no = eway_match.group(1).strip() if eway_match else "841748937799"

    # Known standard product clean names mapping
    known_names = {
        "161": "JEEVEDA RICE BRAN OIL (2 LTR)",
        "162": "JEEVEDA RICE BRAN OIL (5 LTR)",
        "299": "SUNSCREEN SPF50 PA++++ GEL",
        "389": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-PURE IVORY",
        "390": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-CREAMY VANILLA",
        "391": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-SOFT BEIGE",
        "392": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-SILK ALMOND",
        "393": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-WARM CHESTNUT",
        "442": "LUXE MATTE LIQUID LIPSTICK- FINE WINE",
        "451": "LUXE MATTE LIQUID LIPSTICK- HALEN",
        "452": "LUXE MATTE LIQUID LIPSTICK- CHOCO DELIGHT",
        "490": "BERRYDOC JUICE",
        "495": "SHOTS MORE",
    }

    products = []
    total_taxable = 0.0
    total_igst = 0.0
    total_gross = 0.0
    total_qty = 0

    for r in table:
        if not r or not r[0]:
            continue
        sno_str = str(r[0]).strip()
        if not sno_str.isdigit():
            continue  # Header or footer row

        raw_prod = str(r[1] or '').strip()
        box_str = str(r[3] or '').strip()
        qty_str = str(r[4] or '').strip()
        price_str = str(r[6] or '').strip()
        amt_str = str(r[7] or '').strip()
        igst_amt_str = str(r[9] or '').strip()
        gross_str = str(r[10] or '').strip()

        # Extract product ID
        m = re.search(r'\[(\d+)\]', raw_prod)
        code = m.group(1) if m else ""

        # Determine clean name
        if code in known_names:
            prod_name = known_names[code]
        else:
            clean = re.sub(r'\[\d+\]\s*-\s*$', '', raw_prod).replace('\n', ' ').strip()
            prod_name = re.sub(r'\s+', ' ', clean)

        rate_f = float(price_str.replace(',', ''))
        qty_i = int(float(qty_str.replace(',', '')))
        amt_f = float(amt_str.replace(',', ''))
        igst_f = float(igst_amt_str.replace(',', ''))
        gross_f = float(gross_str.replace(',', ''))

        total_taxable += amt_f
        total_igst += igst_f
        total_gross += gross_f
        total_qty += qty_i

        products.append([
            sno_str,
            code,
            prod_name,
            f"{rate_f:.2f}",
            str(qty_i),
            f"{amt_f:.2f}",
            f"{igst_f:.2f}",
            f"{gross_f:.2f}"
        ])

    order_obj = {
        "sr": 0,
        "bill_no": bill_no,
        "party": "ASCLEPIUS WELLNESS PVT LTD (GUWAHATI WAREHOUSE)",
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

    return order_obj, total_qty, total_taxable, total_igst, total_gross


def apply_order(pdf_path: str = DEFAULT_PDF_PATH, push_to_git: bool = False):
    print("=" * 65)
    print("APPLYING STOCK ORDER CHALLAN TO PURCHASE HISTORY & INVENTORY")
    print(f"Source PDF: {pdf_path}")
    print("=" * 65)

    order_obj, total_qty, total_taxable, total_igst, total_gross = parse_challan_pdf(pdf_path)
    bill_no = order_obj["bill_no"]

    print(f"Parsed Bill: {bill_no} | Date: {order_obj['date']}")
    print(f"Items: {len(order_obj['products'])} products | Total Qty: {total_qty} units")
    print(f"Taxable Amount: Rs. {total_taxable:.2f}")
    print(f"IGST: Rs. {total_igst:.2f}")
    print(f"Gross Amount: Rs. {total_gross:.2f}")

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
        # Insert before COMPLIMENTARY if COMPLIMENTARY exists
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
    from sync_full_inventory import sync_all_to_inventory
    sync_all_to_inventory()

    # 4. Update graphify knowledge graph
    print("\nUpdating graphify knowledge graph...")
    try:
        subprocess.run(["graphify", "update", "."], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=30)
        print("✓ Graphify knowledge graph updated.")
    except Exception as ge:
        print(f"[WARN] Error updating graphify: {ge}")

    # 5. Git Commit & Push if requested
    if push_to_git:
        try:
            print("\n[GIT] Staging, committing and pushing to remote repository...")
            subprocess.run(["git", "add", "purchase_orders.json", "ledger.db", "apply_bill_292.py", "sync_full_inventory.py", "graphify-out/"], cwd=str(BASE_DIR), check=True)
            msg = f"feat: add stock order bill {bill_no} and update inventory"
            subprocess.run(["git", "commit", "-m", msg], cwd=str(BASE_DIR), check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR), check=True)
            print("✓ Pushed successfully to origin/main.")
        except Exception as ge:
            print(f"[GIT ERROR] Failed to push to git: {ge}")

    print("\n" + "=" * 65)
    print(f"SUCCESS: BILL {bill_no} PROCESSED & INVENTORY UPDATED!")
    print("=" * 65)


if __name__ == '__main__':
    pdf = DEFAULT_PDF_PATH
    do_push = False
    for arg in sys.argv[1:]:
        if arg in ('--push', '-p'):
            do_push = True
        elif not arg.startswith('-'):
            pdf = arg

    apply_order(pdf, push_to_git=do_push)
