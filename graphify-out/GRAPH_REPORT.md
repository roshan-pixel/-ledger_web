# Graph Report - ledger_web  (2026-09-21)

## Corpus Check
- 288 files · ~129,458 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 768 nodes · 584 edges · 296 communities (276 shown, 20 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `758c3849`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 114|Community 114]]
- [[_COMMUNITY_Community 270|Community 270]]
- [[_COMMUNITY_Community 271|Community 271]]
- [[_COMMUNITY_Community 293|Community 293]]

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 22 edges
2. `🏗️ Deep System Architecture & How It Works` - 11 edges
3. `3. Core Subsystems & Module Breakdown` - 11 edges
4. `init_google_sheets()` - 9 edges
5. `⚡ Ledger God Mode Web App` - 9 edges
6. `📸 Screenshots` - 9 edges
7. `update_inventory_formulas()` - 8 edges
8. `get_sold_qty_col_idx()` - 8 edges
9. `indices` - 8 edges
10. `update_totals_row()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `add_product()` --calls--> `init_google_sheets()`  [INFERRED]
  add_new_product.py → init_gsheets.py
- `add_product()` --calls--> `get_db()`  [INFERRED]
  add_product.py → app.py
- `list_invoices()` --calls--> `get_db()`  [INFERRED]
  invoice_api.py → app.py
- `update_invoice_info()` --calls--> `get_db()`  [INFERRED]
  invoice_api.py → app.py
- `get_next_invoice_no()` --calls--> `get_db()`  [INFERRED]
  invoice_api.py → app.py

## Communities (296 total, 20 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (17): add_product(), api_force_sync(), api_sync_now(), _auto_sync_loop(), Manual trigger: pull from GSheets → check rollover → push back., Manual trigger: pull from GSheets → check rollover → push back., init_google_sheets(), sync_sheets_api() (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (34): 🧮 1. Dynamic Monthly Inventory Engine (`inventory_engine.py`), 🧾 2. Invoice Billing Terminal (`invoice_api.py` Blueprint), 🔄 3. Monthly Auto-Rollover + Hourly GSheets Sync, 🤖 4. Portal Robotics (Playwright 1.44), 🌲 5. Genealogy Downline Crawler (`Full_Tree_Crawler.py`), 🩺 6. Disease Guide, 🔄 After Cloning, 🤖 AWPL Portal — Bill Detail (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (3): api_inventory_master_months(), api_mizoram_bronze(), api_product_sales()

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (25): 1. High-Level Architecture Overview, 2. System Topology Graph (Graphify), 3.10 KPI Dashboard (`/api/kpi`), 3.1 Flask Application Core (`app.py` — 1373 lines), 3.2 Dynamic Inventory Engine (`inventory_engine.py`), 3.3 Monthly Rollover (`monthly_rollover.py`), 3.4 Invoice & Strict Stock Depletion API (`invoice_api.py` — Blueprint), 3.5 Customer Lookup — DB Cache + Live Portal Fallback (`/api/customer`) (+17 more)

### Community 4 - "Community 4"
Cohesion: 0.50
Nodes (3): api_ledger_report(), Return cached ledger entries from ledger_report.json or SQLite ledger_report tab, Return cached ledger entries from ledger_report.json or SQLite ledger_report tab

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (13): 5.1 Invoice Creation & Strict Stock Depletion, 5.2 Auto-Sync Scheduler — Hourly GSheets + Daily Rollover, 5.3 Stock Point Order via Headless Portal Bot, 5.4 BFS Genealogy Downline Tree Crawler, 5.5 Customer DS Lookup — DB Cache + Live Portal Fallback, 5.6 Invoice Cancel & Stock Restoration, 5. Sequence Diagrams & Data Flows, code:mermaid (sequenceDiagram) (+5 more)

### Community 6 - "Community 6"
Cohesion: 0.23
Nodes (10): get_unticked_invoices(), main(), parse_items(), bulk_push_to_portal.py ---------------------- Reads all invoices with is_dispatc, Return list of {description, qty} dicts from the stored JSON., _log(), Submits an order to the AWPL C&F portal (SpdistributorSale.aspx).     items is a, Launch portal submission as a separate subprocess so it survives Gunicorn's (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (11): balance_text, closing_balance, entries, franchise_value, from_date, headers, pages_scraped, row_count (+3 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (11): amount, billedTo, customer_name, date, ds_code, dsCode, grandTotal, grandTotalSP (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.33
Nodes (9): get_unticked_invoices(), log(), login_and_save_session(), main(), fast_bulk_push.py ----------------- Submits ALL unticked invoices to the AWPL po, submit_one(), main(), sync_and_push_latest.py ----------------------- 1. Syncs new invoices from Rende (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (4): api_inventory(), categorize_product(), Categorize an Asclepius product into authentic product lines., Categorize an Asclepius product into authentic product lines.

### Community 11 - "Community 11"
Cohesion: 0.27
Nodes (9): get_week_column(), login_and_get_data(), portal_sync.py — Asclepius C&F Portal → Excel Inventory Sync Engine ───────────, Write portal sale quantities into the Excel Inventory_Master sheet.     Matches, Login to portal, fetch DS Sale Report for date range.     Returns list of {prod, Main entry point for sync., Find which 'Sold Qty (Mon DD-DD)' column the sale_date falls into.     Headers, run_sync() (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.25
Nodes (6): api_customer(), fetch_ds_from_portal(), High-performance live DS code lookup in the AWPL C&F portal:     1. Reuses authe, fix_and_fetch(), fix_sheet(), get_ds_details()

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (27): add_product(), api_inventory_add_product(), api_inventory_master(), api_inventory_master_update(), api_inventory_restock(), api_mizoram_bronze_update(), api_update(), get_db() (+19 more)

### Community 14 - "Community 14"
Cohesion: 0.36
Nodes (8): calculate_inventory(), extract_code(), get_available_months(), get_days_in_month(), parse_date(), inventory_engine.py Dynamic inventory calculator for monthly rollover. Replaces, Scan database invoices and purchase orders to find all unique months., Dynamically computes headers and inventory quantities/values for target_month_st

### Community 15 - "Community 15"
Cohesion: 0.25
Nodes (7): api_disease_guide(), api_disease_guide_detail(), disease_guide(), _load_disease_cache(), Load and flatten the disease JSON into the module-level cache.     Thread-safe;, Return a lightweight list of diseases, optionally filtered.      Query params:, Return the full record for a single disease by its 0-based index     in the fla

### Community 16 - "Community 16"
Cohesion: 0.25
Nodes (7): billedTo, date, dsCode, grandTotal, grandTotalSP, invoiceNo, items

### Community 17 - "Community 17"
Cohesion: 0.29
Nodes (6): dispatched_count, not_registered_in_portal, portal_stock_in_entries, portal_stock_out_entries, raw_stock_in, raw_stock_out

### Community 18 - "Community 18"
Cohesion: 0.38
Nodes (6): _build_week_ranges(), check_and_rollover(), _get_header_month(), monthly_rollover.py ────────────────────────────────────────────────────────────, Read the month that the Sold Qty columns are currently set to.     Returns a (ye, Check whether the inventory_headers month matches the current calendar     month

### Community 19 - "Community 19"
Cohesion: 0.38
Nodes (6): cells_to_item(), main(), parse_detail_page(), Full FSalesInvoiceList scraper. - Date: 01/01/2026 -> today - Scrapes all rows, Parse spSalesInvoiceListDetails.aspx — returns list of product dicts., Convert a detail page row to an invoice item dict.

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (5): currentSort, filterInput, filterWrapper, inventory, table

### Community 21 - "Community 21"
Cohesion: 0.47
Nodes (5): login_and_open(), main(), parse_all_grid_rows(), Portal product scraper — fast version. Column layout from GridView2:   [0] Sr, Return dict {prod_code_str: {name, rate, box_size}} for ALL rows in GridView2.

### Community 22 - "Community 22"
Cohesion: 0.40
Nodes (4): main(), parse_bill_detail(), Full purchase history scraper. - Date range: 01/06/2026 → 26/07/2026 - Fetches, Parse product table from the bill detail page.

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (4): addItemBtn, itemsContainer, row, taxRateInput

### Community 24 - "Community 24"
Cohesion: 0.50
Nodes (4): fetch_ledger_report(), fetch_ledger_report.py  –  Precise multi-page scraper for SpLedgerReport.aspx L, Save scraped ledger report into SQLite database and trigger sync., save_ledger_to_db()

### Community 25 - "Community 25"
Cohesion: 0.40
Nodes (3): parse_orders_table(), Scrape PurchaseListn.aspx for date range 01/06/2026 to 26/07/2026. Also click e, Return list of order dicts from the main GV table.

### Community 26 - "Community 26"
Cohesion: 0.40
Nodes (4): Recalculate the TOTAL row at the bottom., Recalculate formulas for a row., update_inventory_formulas(), update_totals_row()

### Community 27 - "Community 27"
Cohesion: 0.40
Nodes (3): api_sync_mizoram_now(), fix_achieved_status(), sync_mizoram_data()

### Community 28 - "Community 28"
Cohesion: 0.40
Nodes (4): C&F Portal Synchronization Documentation, How It Works, Overview, Running the Sync

### Community 29 - "Community 29"
Cohesion: 0.83
Nodes (3): cells_to_item(), main(), parse_detail_page()

### Community 30 - "Community 30"
Cohesion: 0.50
Nodes (3): submit_stock_order.py  –  Submits a Stock Point (Franchise) Purchase Order, items: list of dicts — { name: str, qty: int, portal_id: str (optional) }     p, submit_stock_order()

### Community 32 - "Community 32"
Cohesion: 0.50
Nodes (3): submit_stock_order.py  –  Submits a Stock Point (Franchise) Purchase Order, items: list of dicts — { name: str, qty: int, portal_id: str (optional) }     p, submit_stock_order()

### Community 36 - "Community 36"
Cohesion: 0.50
Nodes (3): api_ledger_wallet_balance(), Return closing balance for stock-point-order and dashboard sync., Return closing balance for stock-point-order and dashboard sync.

### Community 68 - "Community 68"
Cohesion: 0.67
Nodes (3): api_ledger_manual_entry(), Add a manual entry to the ledger_report.json file., Add a manual entry to the ledger_report.json file.

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (3): api_place_stock_order(), Places a franchise stock point order on the Asclepius portal.     Expects JSON, Places a franchise stock point order on the Asclepius portal.     Expects JSON

### Community 70 - "Community 70"
Cohesion: 0.67
Nodes (3): api_portal_sync(), Run the portal sync directly to SQLite!, Run the portal sync directly to SQLite!

### Community 71 - "Community 71"
Cohesion: 0.67
Nodes (3): api_refresh_wallet(), Trigger fast real-time wallet scrape from portal., Trigger fast real-time wallet scrape from portal.

### Community 72 - "Community 72"
Cohesion: 0.67
Nodes (3): api_sync_remarks_from_gsheets(), Trigger one-way remarks pull from GSheets (no push/upload back)., Trigger one-way remarks pull from GSheets (no push/upload back).

### Community 270 - "Community 270"
Cohesion: 0.12
Nodes (15): all_data, extracted_count, headers, indices, billNoIdx, dateGreenIdx, dateIdx, dsCodeIdx (+7 more)

### Community 293 - "Community 293"
Cohesion: 0.40
Nodes (3): api_kpi(), compute_kpis_data(), dashboard()

## Knowledge Gaps
- **111 isolated node(s):** `all_data`, `extracted_count`, `headers`, `billNoIdx`, `dateGreenIdx` (+106 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db()` connect `Community 13` to `Community 2`, `Community 4`, `Community 293`, `Community 36`, `Community 10`, `Community 12`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Why does `create_invoice()` connect `Community 13` to `Community 6`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `get_db()` (e.g. with `add_product()` and `create_invoice()`) actually correct?**
  _`get_db()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `init_google_sheets()` (e.g. with `add_product()` and `_auto_sync_loop()`) actually correct?**
  _`init_google_sheets()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Load and flatten the disease JSON into the module-level cache.     Thread-safe;`, `Return a lightweight list of diseases, optionally filtered.      Query params:`, `Return the full record for a single disease by its 0-based index     in the fla` to the rest of the system?**
  _188 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09666666666666666 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06050420168067227 - nodes in this community are weakly interconnected._