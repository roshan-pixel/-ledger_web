import os
import re

def fix_invoice():
    path = r'C:\Users\sgarm\Downloads\ledger_web\templates\invoice.html'
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Fix Price (₹)
    content = re.sub(r'Price \([^)]+\)', 'Price (₹)', content)
    # Fix Total (₹)
    content = re.sub(r'Total \([^)]+\)', 'Total (₹)', content)
    # Fix 0.00 amounts
    content = re.sub(r'<span id="subtotalAmt">[^0-9<]+0\.00</span>', '<span id="subtotalAmt">₹0.00</span>', content)
    content = re.sub(r'<span id="grandTotal">[^0-9<]+0\.00</span>', '<span id="grandTotal">₹0.00</span>', content)
    # Fix JS amounts
    content = re.sub(r'\'[^\']+\' \+ fmt\(sub\)', "'₹' + fmt(sub)", content)
    
    # Fix badges and status
    content = re.sub(r'<span class="tax-badge">[^<]+Tax Included</span>', '<span class="tax-badge">✓ Tax Included</span>', content)
    content = re.sub(r"'[^']*Customer found'", "'✓ Customer found'", content)
    content = re.sub(r"\|\| '[^']+'", "|| '—'", content)
    content = re.sub(r"'[^']+DS Code not found[^']+'", "'❌ DS Code not found — please check and try again'", content)
    content = re.sub(r"'Looking up[^']+'", "'Looking up...'", content)
    content = re.sub(r"'[^']+Network error'", "'❌ Network error'", content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_invoice_history():
    path = r'C:\Users\sgarm\Downloads\ledger_web\templates\invoice_history.html'
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Fix Amount (₹)
    content = re.sub(r'Amount \([^)]+\)', 'Amount (₹)', content)
    content = re.sub(r'<title>[^<]+</title>', '<title>Recent Invoices — Nexus Analytics</title>', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_invoice()
fix_invoice_history()
print("Fixed successfully")
