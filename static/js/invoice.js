document.addEventListener('DOMContentLoaded', () => {
    const addItemBtn = document.getElementById('add-item-btn');
    const itemsContainer = document.getElementById('line-items');
    
    function calculateTotals() {
        let subtotal = 0;
        
        // Calculate each row's total
        document.querySelectorAll('.line-item').forEach(row => {
            const qtyInput = row.querySelector('.qty');
            const priceInput = row.querySelector('.price');
            const totalEl = row.querySelector('.item-total');
            
            const qty = parseFloat(qtyInput?.value) || 0;
            const price = parseFloat(priceInput?.value) || 0;
            const total = qty * price;
            
            if (totalEl) {
                if (totalEl.tagName === 'INPUT') {
                    totalEl.value = total.toFixed(2);
                } else {
                    totalEl.textContent = total.toFixed(2);
                }
            }
            
            subtotal += total;
        });
        
        // Update subtotal
        const subtotalEl = document.getElementById('subtotal');
        if (subtotalEl) {
            if (subtotalEl.tagName === 'INPUT') {
                subtotalEl.value = subtotal.toFixed(2);
            } else {
                subtotalEl.textContent = subtotal.toFixed(2);
            }
        }
        
        // Update tax
        const taxRateInput = document.getElementById('tax-rate');
        const taxRate = parseFloat(taxRateInput?.value) || 0;
        const taxAmount = subtotal * (taxRate / 100);
        
        const taxAmountEl = document.getElementById('tax-amount');
        if (taxAmountEl) {
            if (taxAmountEl.tagName === 'INPUT') {
                taxAmountEl.value = taxAmount.toFixed(2);
            } else {
                taxAmountEl.textContent = taxAmount.toFixed(2);
            }
        }
        
        // Update total
        const total = subtotal + taxAmount;
        const totalEl = document.getElementById('total');
        if (totalEl) {
            if (totalEl.tagName === 'INPUT') {
                totalEl.value = total.toFixed(2);
            } else {
                totalEl.textContent = total.toFixed(2);
            }
        }
    }
    
    // Add new line item
    if (addItemBtn && itemsContainer) {
        addItemBtn.addEventListener('click', () => {
            const row = document.createElement('div');
            row.className = 'line-item';
            row.innerHTML = `
                <input type="text" class="desc" placeholder="Description">
                <input type="number" class="qty" value="1" min="1" step="1">
                <input type="number" class="price" value="0.00" min="0" step="0.01">
                <span class="item-total">0.00</span>
                <button type="button" class="remove-btn">Remove</button>
            `;
            itemsContainer.appendChild(row);
            
            // Listeners for new inputs
            row.querySelector('.qty').addEventListener('input', calculateTotals);
            row.querySelector('.price').addEventListener('input', calculateTotals);
            row.querySelector('.remove-btn').addEventListener('click', () => {
                row.remove();
                calculateTotals();
            });
            
            calculateTotals();
        });
    }
    
    // Listeners for existing elements (if any are pre-rendered)
    document.addEventListener('input', (e) => {
        if (e.target.classList.contains('qty') || e.target.classList.contains('price')) {
            calculateTotals();
        }
    });

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-btn')) {
            const row = e.target.closest('.line-item');
            if (row) {
                row.remove();
                calculateTotals();
            }
        }
    });
    
    const taxRateInput = document.getElementById('tax-rate');
    if (taxRateInput) {
        taxRateInput.addEventListener('input', calculateTotals);
    }
});
