import glob
import os

nav_item = '<li class="nav-item" onclick="navigateTo(\'/mizoram_bronze\')">🏆 Mizoram Bronze</li>'

for f in glob.glob('C:/Users/sgarm/Downloads/ledger_web/templates/*.html'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'navigateTo(\'/disease_guide\')' in content and '/mizoram_bronze' not in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'navigateTo(\'/disease_guide\')' in line:
                lines.insert(i + 1, '            ' + nav_item)
                break
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write('\n'.join(lines))
        print(f'Updated {f}')
