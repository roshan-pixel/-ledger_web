import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

print('Checking invoice_items for these items:')
c.execute("SELECT i.invoice_number, i.status, ii.item_id, ii.item_name, ii.quantity FROM invoice_items ii JOIN invoices i ON ii.invoice_id = i.id WHERE ii.item_id IN ('503', '510')")
sold_items = c.fetchall()
sold_503 = 0
sold_510 = 0
for si in sold_items:
    # Only count non-cancelled
    if si[1] != 'cancelled':
        if si[2] == '503': sold_503 += float(si[4])
        if si[2] == '510': sold_510 += float(si[4])
    else:
        print('Cancelled invoice ignored:', si)

print(f'Total sold from invoices table - 503: {sold_503}')
print(f'Total sold from invoices table - 510: {sold_510}')

conn.close()
