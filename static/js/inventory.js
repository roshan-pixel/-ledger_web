document.addEventListener('DOMContentLoaded', () => {
    let inventory = [];
    let currentSort = { column: 'id', direction: 'asc' };
    let currentFilter = '';

    const container = document.getElementById('inventory-container') || document.body;
    
    // Create filter input if it doesn't exist
    let filterInput = document.getElementById('inventory-filter');
    if (!filterInput) {
        const filterWrapper = document.createElement('div');
        filterWrapper.style.marginBottom = '10px';
        filterInput = document.createElement('input');
        filterInput.id = 'inventory-filter';
        filterInput.placeholder = 'Filter inventory...';
        filterWrapper.appendChild(filterInput);
        container.appendChild(filterWrapper);
    }

    // Create table if it doesn't exist
    let table = document.getElementById('inventory-table');
    if (!table) {
        table = document.createElement('table');
        table.id = 'inventory-table';
        table.style.width = '100%';
        table.style.borderCollapse = 'collapse';
        container.appendChild(table);
    }

    const render = () => {
        let data = inventory.filter(item => {
            if (!currentFilter) return true;
            return Object.values(item).some(val => 
                String(val).toLowerCase().includes(currentFilter.toLowerCase())
            );
        });

        if (data.length > 0) {
            const columns = Object.keys(data[0]);
            
            // Ensure sort column is valid
            if (!columns.includes(currentSort.column)) {
                currentSort.column = columns[0];
            }

            data.sort((a, b) => {
                const valA = a[currentSort.column];
                const valB = b[currentSort.column];
                if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
                if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }

        if (data.length === 0 && inventory.length > 0) {
            table.innerHTML = '<tbody><tr><td style="padding: 10px; border: 1px solid #ccc; text-align: center;">No matching items found.</td></tr></tbody>';
            return;
        } else if (inventory.length === 0) {
            table.innerHTML = '<tbody><tr><td style="padding: 10px; border: 1px solid #ccc; text-align: center;">No inventory items available.</td></tr></tbody>';
            return;
        }

        const columns = Object.keys(data[0]);
        
        const thead = document.createElement('thead');
        const trHead = document.createElement('tr');
        trHead.style.backgroundColor = '#f4f4f4';
        
        columns.forEach(col => {
            const th = document.createElement('th');
            th.style.padding = '8px';
            th.style.border = '1px solid #ddd';
            th.style.cursor = 'pointer';
            th.style.textAlign = 'left';
            th.textContent = col.charAt(0).toUpperCase() + col.slice(1) + 
                (currentSort.column === col ? (currentSort.direction === 'asc' ? ' 🔼' : ' 🔽') : '');
            
            th.onclick = () => {
                if (currentSort.column === col) {
                    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSort.column = col;
                    currentSort.direction = 'asc';
                }
                render();
            };
            trHead.appendChild(th);
        });
        thead.appendChild(trHead);

        const tbody = document.createElement('tbody');
        data.forEach(item => {
            const tr = document.createElement('tr');
            columns.forEach(col => {
                const td = document.createElement('td');
                td.style.padding = '8px';
                td.style.border = '1px solid #ddd';
                td.textContent = item[col];
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        table.innerHTML = '';
        table.appendChild(thead);
        table.appendChild(tbody);
    };

    filterInput.addEventListener('input', (e) => {
        currentFilter = e.target.value;
        render();
    });

    // Fetch from /api/inventory
    fetch('/api/inventory')
        .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        })
        .then(data => {
            inventory = data;
            render();
        })
        .catch(err => {
            console.error('Error fetching inventory:', err);
            table.innerHTML = `<tbody><tr><td style="color:red; padding:10px; border: 1px solid #ccc;">Error loading inventory: ${err.message}</td></tr></tbody>`;
        });
});
