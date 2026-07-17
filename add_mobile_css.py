import os
import glob

css_block = """
        /* ── MOBILE OPTIMIZATION ───────────────── */
        @media(max-width: 768px) {
            body { flex-direction: column !important; }
            .sidebar { width: 100% !important; height: auto !important; position: relative !important; padding: 1rem !important; border-right: none !important; border-bottom: 1px solid var(--border) !important; flex-shrink: 0; }
            .nav-menu { flex-direction: row !important; flex-wrap: wrap !important; gap: 0.5rem !important; justify-content: center !important; }
            .nav-item { padding: 0.5rem 0.8rem !important; font-size: 0.85rem !important; }
            .main { padding: 1rem !important; width: 100% !important; overflow-x: hidden !important; }
            .card, .glass-panel { padding: 1rem !important; border-radius: 16px !important; }
            .inv-header, .header-actions { flex-direction: column !important; align-items: flex-start !important; gap: 1rem !important; }
            .inv-title h1 { font-size: 2rem !important; }
            .ds-lookup-row { flex-direction: column !important; align-items: stretch !important; }
            .ds-lookup-row .glass-input { flex: 1 !important; width: 100% !important; }
            .billing-grid { grid-template-columns: 1fr !important; }
            .table-wrap, .table-container { width: 100% !important; overflow-x: auto !important; -webkit-overflow-scrolling: touch !important; }
            table { white-space: nowrap !important; }
            .kpi-grid { grid-template-columns: 1fr !important; }
        }
"""

for file_path in glob.glob('templates/*.html'):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "/* ── MOBILE OPTIMIZATION ───────────────── */" not in content:
        content = content.replace("</style>", css_block + "\n</style>")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated:", file_path)
