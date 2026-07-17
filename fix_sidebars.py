import glob
import re

bad_str = '''            <li class="nav-item" onclick="navigateTo('/disease_guide')">
            <li class="nav-item" onclick="navigateTo('/mizoram_bronze')">🏆 Mizoram Bronze</li>
                <svg'''

good_str = '''            <li class="nav-item" onclick="navigateTo('/disease_guide')">
                <svg'''

insert_target = '''Disease Guide
            </li>'''
            
insert_content = '''Disease Guide
            </li>
            <li class="nav-item" onclick="navigateTo('/mizoram_bronze')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                Mizoram Bronze
            </li>'''

for f in glob.glob('C:/Users/sgarm/Downloads/ledger_web/templates/*.html'):
    if 'mizoram_bronze.html' in f:
        continue
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if bad_str in content:
        content = content.replace(bad_str, good_str)
        
    if 'Mizoram Bronze' not in content:
        content = content.replace(insert_target, insert_content)
        
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print('Fixed', f)
