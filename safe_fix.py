import os
import re

path = r'C:\Users\sgarm\Downloads\ledger_web\templates\inventory_master.html'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix Rupee symbol
content = content.replace("return 'â‚¹'", "return '₹'")

# Fix dashes/em-dashes (only in strings)
content = content.replace("|| 'â€”'", "|| '—'")
content = content.replace(">â€”<", ">—<")

# Fix sort arrows
content = content.replace(">â–²<", ">▲<")
content = content.replace(">â–¼<", ">▼<")
content = content.replace("'â–²'", "'▲'")
content = content.replace("'â–¼'", "'▼'")

# Fix checkmarks and errors (if they exist like o" or o-)
content = content.replace("'o\" ", "'✓ ")
content = content.replace("'o- ", "'❌ ")
content = content.replace("Excel?", "Excel...")
content = content.replace("remarks?", "remarks...")
content = content.replace("Saving?", "Saving...")
content = content.replace("o\" Saved", "✓ Saved")
content = content.replace("o- ' +", "❌ ' +")

# Title
content = re.sub(r'<title>.*</title>', '<title>Inventory Master — Nexus Analytics</title>', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Safe replacement complete")
