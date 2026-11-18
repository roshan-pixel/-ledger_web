# Ledger Web — Objectives & Work Log

Live app: https://ledger-web-app.onrender.com/ (Render auto-deploys from `main` of `roshan-pixel/-ledger_web`)
Last updated: 18 Nov 2026

## Standing rules
- **Never change dispatch status** (`is_dispatched` slider) when updating remarks or payments. Remark updates POST only `{remark}` to `/api/invoice/update/<id>`.
- Verify through the live API (`/api/purchase_orders`, `/api/inventory`, `/api/kpi`, `/api/invoice/list`), not screenshots.
- The Google Sheet `Ledger_Database` (service account) must match the live site.

## Objectives completed (18 Nov 2026)

| # | Objective | Result | Commit |
|---|-----------|--------|--------|
| 1 | Add AWPL portal bill **GUW/000350/26-27** to purchase history | 21 items, ₹3,15,612.08 added; inventory updated | `a6a3930` |
| 2 | Remaining Stock Value up to date | Dashboard challan count now dynamic (was hardcoded "12") | `a8f514f` |
| 3 | Bill pushed to purchase history → stock & KPIs auto-update | Startup runs `robust_sync.sync_all_to_inventory()` on every deploy | `c8bfab7` |
| 4 | Verify purchase history ↔ invoices ↔ inventory ↔ KPIs on live site | Verified via API: 224 SKUs, 2,642 units remaining, ₹13,51,467.92 remaining value, 18 challans, 483 invoices | — |
| 5 | Add new products **GILOY TABLET [312]** (MRP 303, DP 233, SP 1) and **ASCLEPIUS MASSAGE OIL [680]** (MRP 699, DP 499, SP 2) | Added; `add_product` now recalculates only the new row (fixed Render timeout/500) | `1bc12df` |
| 6 | Cross-check Google Sheet (service account) with live site | Fully consistent; KPIs tab now recomputed before upload | `e510fd8` |
| 7 | Audit remarks: amount matches, UTR unique | Audit done; open items listed below | — |
| 8 | WhatsApp slips → DS IDs → update pending invoice remarks | Remarks updated with yellow "✅ Auto-updated via WhatsApp" box; dispatch toggles reverted on request | — |
| 9 | Split **DSR/000518/26-27** — 1 body lotion to DS **62C04A** | DSR/000518 = ₹27,515.99 / 102.25 SP; new **DSR/000530** (ROSHAN SINGH RATHORE) = ₹309 / 1 SP; both remarks show ₹27,825 (UTR 668152099849) split | `38e72de` |

## New API added
`POST /api/invoice/split/<id>` — body `{password, ds_code, customer_name, move:[{code, qty}]}`. Moves whole/partial item quantities into a new invoice (same date, not sent to AWPL portal). Requires the dispatch password.

## Open items (flagged, not yet requested)
- SANGPUII **DSR/000108** carries LALTLANKIMA's UTR 620665263261.
- Remarks on **441–443** reference "DSR/000444" instead of 448 + 449.
- Unexplained overpayments on **182, 212, 266/274, 330**.
- No payment slips found for **476–479** and **482**.
- JOHNSON **290–292** have no remark.
- **DSR/000530** not submitted to AWPL portal (use Resubmit on Recent Invoices if needed).
- "Total Stock Purchased" stays ledger-based (₹40,84,252.40) until the AWPL ledger is re-scraped.
