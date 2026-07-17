import os

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # UI replacements
    content = content.replace('â€”', '—') # em dash
    content = content.replace('â†’', '→') # right arrow
    content = content.replace('â€¦', '...') # ellipsis
    content = content.replace('âš¡', '⚡') # lightning bolt
    content = content.replace('âš\xa0', '⚠️') # warning sign (âš  in some encodings)
    content = content.replace('âš ', '⚠️')
    content = content.replace('âœ—', '❌') # cross
    content = content.replace('âœ“', '✓') # checkmark
    
    # Comment replacements (optional but good for cleanliness)
    content = content.replace('â”€', '─') # line drawing dash

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file(r'C:\Users\sgarm\Downloads\ledger_web\templates\invoice_history.html')
fix_file(r'C:\Users\sgarm\Downloads\ledger_web\templates\portal_sync.html')

print("Final templates fixed safely.")
