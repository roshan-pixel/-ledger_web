with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\mizoram_bronze.html', 'r', encoding='utf-8') as f:
    content = f.read()

target1 = '''    <div class="page-header">
        <div>
            <h1>Mizoram Bronze 2026</h1>
            <p style="color: var(--muted);">Commission Data Overview</p>
        </div>
    </div>'''

replacement1 = '''    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1>Mizoram Bronze 2026</h1>
            <p style="color: var(--muted);">Commission Data Overview</p>
        </div>
        <button class="btn-primary" id="syncBtn" onclick="syncMizoramData()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
            Sync from Google Sheets
        </button>
    </div>'''

content = content.replace(target1, replacement1)

target2 = '''    function navigateTo(url) {'''

replacement2 = '''    async function syncMizoramData() {
        const btn = document.getElementById('syncBtn');
        const origText = btn.innerHTML;
        btn.innerHTML = 'Syncing...';
        btn.disabled = true;
        try {
            const res = await fetch('/api/sync_mizoram_now', {method: 'POST'});
            const data = await res.json();
            if(data.success) {
                alert('Successfully synced from Google Sheets!');
                loadData();
            } else {
                alert('Sync failed: ' + (data.error || 'Unknown error'));
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

with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\mizoram_bronze.html', 'w', encoding='utf-8') as f:
    f.write(content)
