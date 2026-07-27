import json
with open('stock_orders.json', 'r') as f:
    orders = json.load(f)
    for o in orders:
        if o.get('status') != 'completed':
            for i in o.get('items', []):
                if i.get('product_id') in ('503', '510'):
                    print(f"Found {o.get('status')} order {o.get('order_id')} with {i.get('product_id')} (qty: {i.get('quantity')})")
