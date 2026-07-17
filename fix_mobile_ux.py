import os
import glob
import re

comprehensive_mobile_css = """
        /* ── MOBILE OPTIMIZATION ───────────────── */
        @media(max-width: 768px) {
            /* Structural Fixes */
            body { flex-direction: column !important; }
            .sidebar { width: 100% !important; height: auto !important; position: relative !important; padding: 1rem !important; border-right: none !important; border-bottom: 1px solid var(--border) !important; flex-shrink: 0; gap: 1rem !important; }
            
            /* Top Navigation Conversion */
            .nav-menu { flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; justify-content: flex-start !important; padding-bottom: 0.5rem; -webkit-overflow-scrolling: touch; }
            .nav-item { padding: 0.8rem 1.2rem !important; font-size: 1rem !important; gap: 0.5rem !important; min-height: 44px; flex-shrink: 0; }
            
            /* Container Padding Fixes (covers all classes) */
            .main, .main-content { padding: 1rem !important; width: 100% !important; overflow-x: hidden !important; box-sizing: border-box !important; }
            .card, .glass-panel, .sync-card, .results-card, .auto-card, .kpi-card { padding: 1rem !important; border-radius: 16px !important; box-sizing: border-box !important; width: 100% !important; }
            
            /* Header & Layout Fixes */
            .inv-header, .header-actions, .header { flex-direction: column !important; align-items: flex-start !important; gap: 1rem !important; }
            .inv-title h1, h1 { font-size: 2rem !important; }
            
            /* Forms, Inputs & iOS Zoom Fix */
            .ds-lookup-row, .filters { flex-direction: column !important; align-items: stretch !important; gap: 1rem !important; }
            .ds-lookup-row .glass-input, .filter-input, .filter-select, .glass-input { flex: 1 !important; width: 100% !important; box-sizing: border-box !important; }
            input, select, textarea { font-size: 16px !important; } /* Prevents iOS Keyboard Zoom */
            
            /* Grid & Table Breakpoints */
            .billing-grid, .kpi-grid { grid-template-columns: 1fr !important; }
            .table-wrap, .table-container { width: 100% !important; overflow-x: auto !important; -webkit-overflow-scrolling: touch !important; padding-bottom: 1rem; }
            table { white-space: nowrap !important; }
            thead th { font-size: 0.85rem !important; }
            .total-row { width: 100% !important; }
            
            /* Touch Target Accessibility (Min 44px) */
            .btn, .lookup-btn, .sync-btn { min-height: 44px; padding: 0.8rem 1.5rem !important; width: 100%; text-align: center; justify-content: center; }
            .btn-cancel, .remove-btn, .preset-btn, .filter-btn, .refresh-btn { min-height: 44px; padding: 0.8rem 1.2rem !important; font-size: 1rem !important; }
            
            /* Fixed Elements */
            #saveIndicator { bottom: 5rem !important; right: 1rem !important; padding: 0.8rem 1.2rem !important; }
            
            /* Contrast Fixes */
            .log-card { overflow-x: auto; color: #cbd5e1 !important; background: rgba(0,0,0,0.6) !important; }
            label, thead th { color: #cbd5e1 !important; }
            .glass-input { border-color: rgba(255,255,255,0.2) !important; }
        }
"""

def process_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace the old mobile optimization block
    start_marker = "/* ── MOBILE OPTIMIZATION ───────────────── */"
    end_marker = "</style>"
    
    if start_marker in content:
        # Cut out everything from start_marker to </style>
        before_css = content.split(start_marker)[0]
        # Find </style> after the start marker
        content = before_css + comprehensive_mobile_css + "\n</style>" + content.split(start_marker)[1].split("</style>", 1)[1]
    
    # 2. Specific HTML fixes
    # Replace double-click with click in inventory_master.html
    if "inventory_master.html" in file_path:
        content = content.replace('ondblclick="editCell(this,', 'onclick="editCell(this,')
        # Make the first column sticky
        sticky_css = ".table-container td:first-child, .table-container th:first-child { position: sticky; left: 0; background: rgba(15, 23, 42, 0.95); z-index: 2; }"
        if sticky_css not in content:
            content = content.replace("</style>", "        " + sticky_css + "\n</style>")
        
    # Add min-width to invoice table and remove inline widths
    if "invoice.html" in file_path:
        content = content.replace('<table id="itemsTable">', '<table id="itemsTable" style="min-width: 600px;">')
        content = content.replace('style="width: 190px;"', '')
        
    # Update viewport meta to prevent zoom on all pages
    old_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    new_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
    content = content.replace(old_meta, new_meta)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Processed: {file_path}")

for file_path in glob.glob('templates/*.html'):
    process_html_file(file_path)
