import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

c.execute("SELECT row_num, c2, c3, c7, c27 FROM inventory WHERE c2 IN ('503', '510') OR UPPER(c3) LIKE '%CALCIUM%' OR UPPER(c3) LIKE '%DAYLIFT%'")
rows = c.fetchall()
print('Inventory Rows (row, id, name, total_qty_bought, remaining_qty):')
for r in rows:
    print(r)

c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
sold_idx = next(i for i, h in enumerate(headers) if h == 'Total Qty Sold') + 1

c.execute(f"SELECT c2, c{sold_idx} FROM inventory WHERE c2 IN ('503', '510')")
print('\nTotal Sold (from inventory table columns):')
for r in c.fetchall():
    print(r)

print('\nChecking stock_orders.json for items:')
try:
    with open('stock_orders.json', 'r') as f:
        orders = json.load(f)
    bought_503 = 0
    bought_510 = 0
    for o in orders:
        if o.get('status') == 'completed':
            for item in o.get('items', []):
                if item.get('product_id') == '503': bought_503 += int(item.get('quantity', 0))
                if item.get('product_id') == '510': bought_510 += int(item.get('quantity', 0))
    print(f'Bought 503: {bought_503}')
    print(f'Bought 510: {bought_510}')
except Exception as e:
    print("Error parsing stock_orders.json:", e)

print('\nChecking invoice_items for these items:')
c.execute("SELECT i.invoice_number, i.date_created, ii.item_id, ii.item_name, ii.quantity FROM invoice_items ii JOIN invoices i ON ii.invoice_id = i.id WHERE ii.item_id IN ('503', '510') AND i.status != 'cancelled'")
sold_items = c.fetchall()
sold_503 = 0
sold_510 = 0
for si in sold_items:
    print(si)
    if si[2] == '503': sold_503 += int(si[4])
    if si[2] == '510': sold_510 += int(si[4])

print(f'\nTotal sold from invoices table - 503: {sold_503}')
print(f'Total sold from invoices table - 510: {sold_510}')

conn.close()
