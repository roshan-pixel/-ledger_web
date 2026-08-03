import requests
import json
import time

BASE_URL = 'https://ledger-web-app.onrender.com'

# 1. Fetch invoice 112
print("Fetching invoice 112...")
res = requests.get(f'{BASE_URL}/api/invoice/list')
invoices = res.json().get('invoices', [])
inv = next(i for i in invoices if i['id'] == 112)

# 2. Cancel invoice 112
print("Cancelling invoice 112...")
cancel_res = requests.post(f'{BASE_URL}/api/invoice/cancel/112')
print(cancel_res.json())

# Wait a couple of seconds to ensure DB and stock are updated
time.sleep(3)

# 3. Create new corrected invoice
new_items = []
for item in inv['items']:
    desc = item.get('description', '')
    if '503' in desc:
        print("Dropping Calcium Tablet (was 0 stock).")
        continue
    elif '510' in desc:
        print("Reducing Daylift Tablet from 3 to 2 (max stock).")
        item['qty'] = '2'
        item['total'] = str(float(item['price']) * 2)
        item['total_sp'] = str(float(item['unit_sp']) * 2)
        new_items.append(item)
    else:
        new_items.append(item)

grand_total = sum(float(i['total']) for i in new_items)
grand_total_sp = sum(float(i['total_sp']) for i in new_items)

new_invoice = {
    'invoiceNo': inv['invoice_no'],
    'dsCode': inv['ds_code'],
    'billedTo': inv['customer_name'],
    'date': inv['date_created'],
    'items': new_items,
    'grandTotal': grand_total,
    'grandTotalSP': grand_total_sp,
    'orderType': 'sao'
}

print(f"Creating new invoice: Total={grand_total}, SP={grand_total_sp}")
create_res = requests.post(f'{BASE_URL}/api/invoice/create', json=new_invoice)
print(create_res.json())
