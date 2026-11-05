---
type: "query"
date: "2026-11-05T08:01:13.276345+00:00"
question: "What stock was added for bill GUW/000341/26-27 and is the Remaining Stock Value KPI currently accurate?"
contributor: "graphify"
source_nodes: ["sync_purchase_bill.py", "inventory_engine.py", "app.py", "sync_full_inventory.py"]
---

# Q: What stock was added for bill GUW/000341/26-27 and is the Remaining Stock Value KPI currently accurate?

## Answer

Bill GUW/000341/26-27 (dated 03/11/2026, Rs.235232.22, 33 line items) was fetched from the AWPL portal via sync_purchase_bill.py and merged into purchase_orders.json + ledger.db (commit 7cc368c). Separately, the Remaining Stock Value KPI on the dashboard was found to be overstated by ~Rs.3.13 lakh (1627004.27 shown vs 1313153.16 correct) because 8 SKUs (GYNEDOC RAS [46], TOSHINE DETERGENT BAR [258], ULTRA SMOOTHING SERUM [376], ULTRA SMOOTH FOUNDATION-CREAMY VANILLA [390], OMEGADOC CAPSULE [492], VITMIN B12 TABLET [501], DAYLIFT TABLET [510], MORIDOC TABLET [498]) were 100% sold out per invoice history but still showed full purchased qty as remaining. Root cause: app.py's update_inventory_formulas() re-invokes inventory_engine.calculate_inventory() once per inventory row (222x) during sync_full_inventory.sync_all_to_inventory(), and this per-row re-matching was observed to be FLAKY/non-deterministic in testing (same input gave Remaining Qty 0 in one run, 24 in the next, with no exception logged) -- suspected race with the _auto_sync_loop background thread that app.py starts on import. Fixed by writing a one-shot script that calls inventory_engine.calculate_inventory(conn) ONCE and writes all 222 rows' columns directly keyed by the engine's own '__row' field (bypassing the flaky per-row path), committed as 94788e3. The underlying flakiness in update_inventory_formulas/sync_full_inventory.py is NOT fixed and could resurface on the next sync.

## Source Nodes

- sync_purchase_bill.py
- inventory_engine.py
- app.py
- sync_full_inventory.py