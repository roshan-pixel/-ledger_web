import os
import glob
import re

template_dir = r'C:\Users\sgarm\Downloads\ledger_web\templates'
html_files = glob.glob(os.path.join(template_dir, '*.html'))

new_logo_html = '''<div class="logo" style="text-align: center; padding: 1rem 0;">
        <img src="{{ url_for('static', filename='logo.png') }}" alt="Asclepius Wellness" style="max-width: 85%; height: auto; background: linear-gradient(135deg, rgba(255,255,255,1) 0%, rgba(220,225,235,1) 100%); border-radius: 16px; padding: 12px; box-shadow: 0 8px 32px rgba(99, 102, 241, 0.15), inset 0 0 0 1px rgba(255,255,255,0.5);">
    </div>'''

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Target the sidebar logo ONLY, not the one inside invoice printable header
    if '<!-- â”€â”€ SIDEBAR' in content or '<!-- ── SIDEBAR' in content or '<aside class="sidebar">' in content:
        # replace only the first occurrence of <div class="logo">
        content = re.sub(r'<div class="logo"[^>]*>.*?</div>', new_logo_html, content, count=1, flags=re.DOTALL)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {os.path.basename(file_path)}')
