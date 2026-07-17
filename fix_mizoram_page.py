import os

with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\inventory_master.html', 'r', encoding='utf-8') as f:
    master = f.read()

# Make sure we got it
idx = master.find('<main class="main">')
if idx == -1:
    print("Could not find main class main")
    idx = master.find('<main')

header_part = master[:idx]

# IMPORTANT: I must make sure that the Mizoram sidebar link is marked 'active' 
# and inventory_master is NOT active.
header_part = header_part.replace('<li class="nav-item active" onclick="navigateTo(\'/inventory_master\')">', '<li class="nav-item" onclick="navigateTo(\'/inventory_master\')">')
header_part = header_part.replace('<li class="nav-item" onclick="navigateTo(\'/mizoram_bronze\')">', '<li class="nav-item active" onclick="navigateTo(\'/mizoram_bronze\')">')


mizoram_specific = '''<main class="main">
    <div class="page-header">
        <div>
            <h1>Mizoram Bronze 2026</h1>
            <p style="color: var(--muted);">Commission Data Overview</p>
        </div>
    </div>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>DS ID</th>
                    <th>DS Name</th>
                    <th>Bronze Comm</th>
                    <th>Bronze Achieved</th>
                    <th>Bronze Date</th>
                    <th>Silver Comm</th>
                    <th>Silver Achieved</th>
                    <th>Silver Date</th>
                    <th>Gold Comm</th>
                    <th>Gold Achieved</th>
                    <th>Gold Date</th>
                    <th>Platinum Comm</th>
                    <th>Platinum Achieved</th>
                    <th>Platinum Date</th>
                    <th>Phone No.</th>
                </tr>
            </thead>
            <tbody id="tableBody">
                <tr><td colspan="15" style="text-align:center; color: var(--muted); padding: 2rem;">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</main>

<script>
    async function loadData() {
        try {
            const res = await fetch('/api/mizoram_bronze');
            const data = await res.json();
            
            const tbody = document.getElementById('tableBody');
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="15" style="text-align:center; color: var(--muted); padding: 2rem;">No data available</td></tr>';
                return;
            }

            const formatAchieved = (val) => {
                val = val ? val.toString().trim() : '';
                if (val.toUpperCase() === 'YES') {
                    return `<span class="badge badge-in">YES</span>`;
                } else if (val.toUpperCase() === 'NO') {
                    return `<span class="badge badge-out">NO</span>`;
                }
                return val;
            };

            const rowsHtml = data.map(r => `
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
            `).join('');
            
            tbody.innerHTML = rowsHtml;
        } catch(e) {
            console.error(e);
            document.getElementById('tableBody').innerHTML = '<tr><td colspan="15" style="text-align:center; color: #ef4444; padding: 2rem;">Failed to load data</td></tr>';
        }
    }
    document.addEventListener('DOMContentLoaded', loadData);
    
    function navigateTo(url) {
        document.body.style.opacity = '0';
        document.body.style.transition = 'opacity .25s ease-out';
        setTimeout(() => { window.location.href = url; }, 260);
    }
</script>
</body>
</html>
'''

with open(r'C:\Users\sgarm\Downloads\ledger_web\templates\mizoram_bronze.html', 'w', encoding='utf-8') as f:
    f.write(header_part + mizoram_specific)
print('Fixed mizoram_bronze.html layout!')
