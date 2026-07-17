import glob, re

mizoram_good = '''            <li class="nav-item{active}" onclick="navigateTo('/mizoram_bronze')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                Mizoram Bronze
            </li>'''

for file in glob.glob(r'C:\Users\sgarm\Downloads\ledger_web\templates\*.html'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    changed = False
    
    # 1. Remove the bad nested Mizoram line
    bad_pattern = re.compile(r'\s*<li class="nav-item.*?" onclick="navigateTo\(\'/mizoram_bronze\'\)">🏆 Mizoram Bronze</li>')
    if bad_pattern.search(content):
        content = bad_pattern.sub('', content)
        changed = True
        
    # 2. Check if Mizoram Bronze exists in a GOOD format (has the SVG).
    if 'Mizoram Bronze\n' not in content:
        # Determine if it should be active
        is_active = ' active' if 'mizoram_bronze.html' in file else ''
        good_li = mizoram_good.replace('{active}', is_active)
        
        # Append before </ul>
        content = content.replace('        </ul>', good_li + '\n        </ul>')
        changed = True
        
    if changed:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed {file}')
