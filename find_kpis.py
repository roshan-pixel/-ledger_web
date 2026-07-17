import re
with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()
    for i, line in enumerate(text.split('\n')):
        if 'id="' in line and ('kpi' in line or 'val' in line or 'qty' in line) or 'document.getElementById' in line or 'fetch' in line:
            print(f"{i+1}: {line.strip()}")
