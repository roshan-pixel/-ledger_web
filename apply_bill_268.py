import json
import sqlite3
import shutil
import re
import os
from bs4 import BeautifulSoup

def main():
    print("=" * 60)
    print("APPLYING BILL GUW/000268/26-27 TO PURCHASE HISTORY & INVENTORY")
    print("=" * 60)

    # 1. Backups
    shutil.copyfile('purchase_orders.json', 'purchase_orders.json.bak')
    shutil.copyfile('ledger.db', 'ledger.db.bak')
    print("✓ Backups created: purchase_orders.json.bak and ledger.db.bak")

    # 2. Extract products from detail page html
    with open('scratch/detail_page.html', 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    gv = soup.find('table', id='ctl00_ContentPlaceHolder1_GV')
    rows = gv.find_all('tr')

    products = []
    total_amt = 0.0
    total_tax = 0.0
    total_net = 0.0
    total_qty = 0

    for tr in rows[1:]:
        tds = [td.text.strip() for td in tr.find_all('td')]
        if tds and len(tds) >= 8 and tds[1] != 'Total ----->>':
            sno, code, name, rate, qty, amount, tax_rate, net_amt = tds[:8]
            amt_f = float(amount.replace(',', ''))
            net_f = float(net_amt.replace(',', ''))
            tax_f = round(net_f - amt_f, 2)
            qty_i = int(float(qty.replace(',', '')))
            rate_f = float(rate.replace(',', ''))
            
            total_amt += amt_f
            total_tax += tax_f
            total_net += net_f
            total_qty += qty_i
            
            products.append([
                sno,
                code,
                name,
                f"{rate_f:.2f}",
                str(qty_i),
                f"{amt_f:.2f}",
                f"{tax_f:.2f}",
                f"{net_f:.2f}"
            ])

    print(f"✓ Parsed {len(products)} products ({total_qty} units, Net: Rs. {total_net:.2f}, Tax: Rs. {total_tax:.2f})")

    new_order = {
        "sr": 12,
        "bill_no": "GUW/000268/26-27",
        "party": "ASCLEPIUS WELLNESS PVT LTD (GUWAHATI WAREHOUSE)",
        "date": "19/09/2026",
        "cgst": "0.00",
        "sgst": "0.00",
        "igst": f"{total_tax:.2f}",
        "total": f"{total_net:.2f}",
        "lr_no": "118310",
        "delivery_date": "19/09/2026",
        "courier": "INDIA COURIER SERVICE",
        "products": products
    }

    # 3. Update purchase_orders.json
    with open('purchase_orders.json', 'r', encoding='utf-8') as f:
        orders = json.load(f)

    # Filter out total row and check if already present
    clean_orders = [o for o in orders if o.get('party') != 'Total']
    
    # Check if GUW/000268/26-27 exists
    existing_idx = None
    for i, o in enumerate(clean_orders):
        if o.get('bill_no') == 'GUW/000268/26-27':
            existing_idx = i
            break

    if existing_idx is not None:
        print(f"Bill GUW/000268/26-27 already exists in purchase_orders.json at index {existing_idx}. Updating in place.")
        clean_orders[existing_idx] = new_order
    else:
        # Insert before COMPLIMENTARY if COMPLIMENTARY exists, or at end
        comp_idx = None
        for i, o in enumerate(clean_orders):
            if o.get('bill_no') == 'COMPLIMENTARY':
                comp_idx = i
                break
        
        if comp_idx is not None:
            clean_orders.insert(comp_idx, new_order)
        else:
            clean_orders.append(new_order)

    # Re-index sr
    for idx, o in enumerate(clean_orders):
        o['sr'] = idx + 1

    # Recalculate grand totals
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

    with open('purchase_orders.json', 'w', encoding='utf-8') as f:
        json.dump(updated_orders, f, indent=2)

    print(f"✓ Saved purchase_orders.json ({len(clean_orders)} orders + Grand Total: Rs. {grand_total:.2f})")

    # 4. Run inventory sync to recalculate all stock quantities and formulas
    print("\nRunning sync_all_to_inventory()...")
    from sync_full_inventory import sync_all_to_inventory
    sync_all_to_inventory()

    print("\n" + "=" * 60)
    print("SUCCESS: GUW/000268/26-27 PROCESSED AND INVENTORY FULLY UPDATED")
    print("=" * 60)

if __name__ == '__main__':
    main()
