from app import app
import json

with app.test_client() as c:
    res = c.get('/api/inventory')
    data = res.get_json()
    for row in data.get('data', []):
        name = row.get('Product Name', '')
        if '503' in name or '510' in name:
            print(f"{name} -> Total Qty: {row.get('Total Qty')}, Remaining: {row.get('Remaining Qty')}")
