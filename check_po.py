import json
import re

print("Checking purchase_orders.json")
try:
    with open('purchase_orders.json', 'r', encoding='utf-8') as f:
        purchases = json.load(f)
    
    total_503 = 0
    total_510 = 0
    for order in purchases:
        for prod in order.get('products', []):
            if len(prod) >= 5:
                code = str(prod[1]).strip()
                try:
                    qty = float(str(prod[4]).replace(',', ''))
                except:
                    qty = 0
                if code == '503': total_503 += qty
                if code == '510': total_510 += qty
                
    print(f'Total bought 503: {total_503}')
    print(f'Total bought 510: {total_510}')
except Exception as e:
    print(e)
