with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\inventory_master.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        <button class="btn-primary" onclick="window.location.href='/invoice'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            New Invoice
        </button>'''

replacement = '''        <button class="btn-primary" id="fixBucketsBtn" onclick="fixBuckets()" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); margin-right: 10px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12h4l2-9 5 18 3-9h4"></path></svg>
            Fix Inventory History
        </button>
        <button class="btn-primary" onclick="window.location.href='/invoice'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            New Invoice
        </button>'''

content = content.replace(target, replacement)

target2 = '''    function navigateTo(url) {'''
replacement2 = '''    async function fixBuckets() {
        if(!confirm('This will recalculate all historical inventory buckets and push to Google Sheets. Continue?')) return;
        const btn = document.getElementById('fixBucketsBtn');
        const origText = btn.innerHTML;
        btn.innerHTML = 'Fixing...';
        btn.disabled = true;
        try {
            const res = await fetch('/api/fix_historical_buckets', {method: 'POST'});
            const data = await res.json();
            if(data.success) {
                alert('Inventory History successfully fixed!\\n' + data.output);
                window.location.reload();
            } else {
                alert('Fix failed: ' + data.error);
            }
        } catch(e) {
            alert('Error connecting to server.');
        } finally {
            btn.innerHTML = origText;
            btn.disabled = false;
        }
    }
    
    function navigateTo(url) {'''

content = content.replace(target2, replacement2)

with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\inventory_master.html', 'w', encoding='utf-8') as f:
    f.write(content)
