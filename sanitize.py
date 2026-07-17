import glob
import os

def clean_all_mojibake():
    template_dir = r'C:\Users\sgarm\Downloads\ledger_web\templates'
    for path in glob.glob(os.path.join(template_dir, '*.html')):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        original = content

        # Safe text replacements
        content = content.replace('â€”', '—')  # em dash
        content = content.replace('â€¦', '...') # ellipsis
        content = content.replace('â”€', '─')  # box drawing dash (used in comments)
        content = content.replace('â†’', '→')  # right arrow
        content = content.replace('âš¡', '⚡') # lightning
        content = content.replace('âš\xa0', '⚠️') # warning
        content = content.replace('âš ', '⚠️') # warning
        content = content.replace('âœ—', '❌') # cross
        content = content.replace('âœ“', '✓') # check
        content = content.replace('â‚¹', '₹') # rupee

        if content != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Cleaned {os.path.basename(path)}")

clean_all_mojibake()
