import urllib.request
import json
req = urllib.request.Request("http://localhost:5000/api/inventory")
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())
    
for row in data['data']:
    name = row.get('Product Name', '')
    if '252' in name or '25' in name or '685' in str(row.get('Price/Pc (Rs.)', '')):
        print(repr(name), row.get('Price/Pc (Rs.)'))
