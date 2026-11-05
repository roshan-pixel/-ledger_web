---
type: "query"
date: "2026-11-05T08:01:24.443695+00:00"
question: "Why does the live ledger-web-app.onrender.com show different invoice/dispatch counts than the local ledger.db in this repo, and what is the risk of pushing local ledger.db changes?"
contributor: "graphify"
source_nodes: ["app.py", "render.yaml", "Dockerfile", "invoice_api.py"]
---

# Q: Why does the live ledger-web-app.onrender.com show different invoice/dispatch counts than the local ledger.db in this repo, and what is the risk of pushing local ledger.db changes?

## Answer

On 2026-11-05 local ledger.db showed 437 invoices / 42 unticked (undispatched) / Remaining Value 1313153.16 (after fix), but the LIVE site (fetched via /api/invoice/list and /api/kpi) showed 438 invoices / 39 unticked / Remaining Value 1289122.11 -- none of these three numbers match either the pre-fix or post-fix local state. This means the live Render deployment's ledger.db has drifted independently from the git-tracked local copy (someone created an invoice and ticked several as dispatched directly on the live site, and/or background auto-sync on the live instance has run its own recompute cycles). CRITICAL RISK: Dockerfile uses 'COPY . .' and render.yaml has no persistent disk entry, so DB_PATH='ledger.db' is baked into the git-checked-out image at each deploy. If Render auto-deploy is enabled and has not yet picked up the latest push (7cc368c, 94788e3) at the time this was discovered, the NEXT deploy will overwrite the live ledger.db with the git-committed version -- silently discarding any invoices/dispatch-ticks/remarks created directly on the live site that were never pulled back into the local repo and committed. No render CLI or API key was available in this session to confirm deploy status directly; only inferred from API responses. Before pushing ledger.db changes again, pull the live site's current /api/invoice/list and /api/kpi state first and reconcile, or confirm with the user whether Render has a persistent disk for ledger.db that render.yaml does not show.

## Source Nodes

- app.py
- render.yaml
- Dockerfile
- invoice_api.py