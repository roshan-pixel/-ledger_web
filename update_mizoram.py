with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\mizoram_bronze.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''            const rowsHtml = data.map(r => `
                <tr>
                    <td><strong>${r.ds_id || ''}</strong></td>
                    <td class="product">${r.ds_name || ''}</td>
                    <td class="numeric">${r.bronze_commission || ''}</td>
                    <td>${formatAchieved(r.bronze_achieved)}</td>
                    <td>${r.mizoram_bronze_date || ''}</td>
                    <td class="numeric">${r.silver_commission || ''}</td>
                    <td>${formatAchieved(r.silver_achieved)}</td>
                    <td>${r.silver_update_date || ''}</td>
                    <td class="numeric">${r.gold_commission || ''}</td>
                    <td>${formatAchieved(r.gold_achieved)}</td>
                    <td>${r.gold_update_date || ''}</td>
                    <td class="numeric">${r.platinum_commission || ''}</td>
                    <td>${formatAchieved(r.platinum_achieved)}</td>
                    <td>${r.platinum_update_date || ''}</td>
                    <td class="numeric">${r.phone_no || ''}</td>
                </tr>
            `).join('');'''

replacement = '''            const rowsHtml = data.map(r => `
                <tr>
                    <td><strong>${r.ds_id || ''}</strong></td>
                    <td class="product">${r.ds_name || ''}</td>
                    <td class="numeric" style="font-weight:600; color:var(--text-primary);">₹ 1,399</td>
                    <td>${formatAchieved(r.bronze_achieved)}</td>
                    <td>${r.mizoram_bronze_date || ''}</td>
                    <td class="numeric" style="font-weight:600; color:var(--text-primary);">₹ 2,500</td>
                    <td>${formatAchieved(r.silver_achieved)}</td>
                    <td>${r.silver_update_date || ''}</td>
                    <td class="numeric" style="font-weight:600; color:var(--text-primary);">₹ 4,690</td>
                    <td>${formatAchieved(r.gold_achieved)}</td>
                    <td>${r.gold_update_date || ''}</td>
                    <td class="numeric" style="font-weight:600; color:var(--text-primary);">₹ 15,000</td>
                    <td>${formatAchieved(r.platinum_achieved)}</td>
                    <td>${r.platinum_update_date || ''}</td>
                    <td class="numeric">${r.phone_no || ''}</td>
                </tr>
            `).join('');'''

content = content.replace(target, replacement)

target2 = '''            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="15" style="text-align:center; color: var(--muted); padding: 2rem;">No data available</td></tr>';
                return;
            }'''

replacement2 = '''            if (data.length === 0) {
                // Automatically sync if empty!
                tbody.innerHTML = '<tr><td colspan="15" style="text-align:center; color: var(--muted); padding: 2rem;">Auto-syncing from Google Sheets... Please wait!</td></tr>';
                await syncMizoramData(true);
                return;
            }'''

content = content.replace(target2, replacement2)

target3 = '''    async function syncMizoramData() {'''
replacement3 = '''    async function syncMizoramData(isAuto = false) {'''

content = content.replace(target3, replacement3)

target4 = '''            if(data.success) {
                alert('Successfully synced from Google Sheets!');
                loadData();
            } else {'''
replacement4 = '''            if(data.success) {
                if(isAuto !== true) alert('Successfully synced from Google Sheets!');
                // if it was auto, avoid alert
                if(isAuto === true) {
                    // prevent infinite loop if sheet is literally empty
                    if(document.getElementById('tableBody').innerHTML.includes('Auto-syncing')) {
                        // try to load again just once
                        const res2 = await fetch('/api/mizoram_bronze');
                        const data2 = await res2.json();
                        if(data2.length > 0) {
                            loadData();
                        } else {
                            document.getElementById('tableBody').innerHTML = '<tr><td colspan="15" style="text-align:center; color: var(--muted); padding: 2rem;">Google Sheet is currently empty.</td></tr>';
                        }
                    }
                } else {
                    loadData();
                }
            } else {'''

content = content.replace(target4, replacement4)

with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\mizoram_bronze.html', 'w', encoding='utf-8') as f:
    f.write(content)
