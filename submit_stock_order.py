"""
submit_stock_order.py  –  Submits a Stock Point (Franchise) Purchase Order
                           to the Asclepius portal via FranchiseorderN.aspx

Confirmed field IDs from page inspection:
  Product dropdown : ctl00_ContentPlaceHolder1_itemlist
  Qty input        : ctl00_ContentPlaceHolder1_txtqty
  Add button       : ctl00_ContentPlaceHolder1_btnadd
  Save button      : ctl00_ContentPlaceHolder1_ButtonSave1  (value="Send For Approval")

Usage:
  python submit_stock_order.py '<json_items>'

Where json_items is a JSON array like:
  '[{"name": "JC OIL", "qty": 10, "portal_id": "41"}, ...]'

Output:
  JSON to STDOUT with success/error and order details.
"""

import sys
import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://asclepiuswellness.com/login.aspx?webid=1"
ORDER_URL = "https://asclepiuswellness.com/shoppingpoint/FranchiseorderN.aspx"

USERNAME = "AAZFD8117G"
PASSWORD = "ABC@1234"

# Confirmed selectors
SEL_PRODUCT  = "#ctl00_ContentPlaceHolder1_itemlist"
SEL_QTY      = "#ctl00_ContentPlaceHolder1_txtqty"
SEL_ADD      = "#ctl00_ContentPlaceHolder1_btnadd"
SEL_SAVE     = "#ctl00_ContentPlaceHolder1_ButtonSave1"


def submit_stock_order(items: list) -> dict:
    """
    items: list of dicts — { name: str, qty: int, portal_id: str (optional) }
    portal_id is the numeric option value in the itemlist dropdown.
    """
    log = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            # Auto-accept all JS dialogs (save confirmations, alerts)
            def handle_dialog(dialog):
                log.append(f"[PORTAL DIALOG] {dialog.message[:100]}")
                dialog.accept()
            page.on("dialog", handle_dialog)

            # ── 1. Login ──────────────────────────────────────────────────────
            log.append("Logging in…")
            page.goto(LOGIN_URL, wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtspUserid']", USERNAME, force=True)
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtsppassword']", PASSWORD, force=True)
            page.click("input[name='ctl00$ContentPlaceHolder1$btnfranlogin']", force=True)
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(1500)
            log.append(f"Logged in. Now at: {page.url}")

            # ── 2. Go to Franchise Purchase Order Form ────────────────────────
            log.append(f"Going to: {ORDER_URL}")
            page.goto(ORDER_URL, wait_until="networkidle")
            page.wait_for_timeout(2000)
            log.append(f"Order page URL: {page.url}")

            if "error" in page.url.lower():
                return {
                    "success": False,
                    "error": f"Portal returned error page: {page.url}",
                    "log": log,
                }

            # ── 3. Read all product options from itemlist ─────────────────────
            options = page.evaluate(f'''() => {{
                const sel = document.querySelector("{SEL_PRODUCT}");
                if (!sel) return [];
                return Array.from(sel.options).map(o => ({{
                    val: o.value,
                    text: o.text.trim().toUpperCase()
                }})).filter(o => o.val && o.val !== "0");
            }}''')
            log.append(f"Found {len(options)} products in portal dropdown.")

            if not options:
                return {
                    "success": False,
                    "error": "Product dropdown not found or empty on the order page.",
                    "log": log,
                }

            # ── 4. Add each item ──────────────────────────────────────────────
            added = []
            failed = []

            for item in items:
                raw_name  = item.get("name", "").strip()
                item_name = raw_name.upper()
                qty       = int(item.get("qty", 0))
                portal_id = str(item.get("portal_id", "")).strip()

                if not item_name or qty <= 0:
                    continue

                # Find best matching option
                best_val  = None
                best_text = None

                # 1. Exact portal_id match (most reliable)
                if portal_id:
                    for opt in options:
                        if opt["val"] == portal_id:
                            best_val  = opt["val"]
                            best_text = opt["text"]
                            break

                # 2. Exact name match
                if not best_val:
                    for opt in options:
                        if item_name == opt["text"] or item_name in opt["text"]:
                            best_val  = opt["val"]
                            best_text = opt["text"]
                            break

                # 3. Word-overlap fuzzy match
                if not best_val:
                    words = [w for w in item_name.split() if len(w) > 2]
                    best_score = 0
                    for opt in options:
                        score = sum(1 for w in words if w in opt["text"])
                        if score > best_score:
                            best_score = score
                            best_val   = opt["val"]
                            best_text  = opt["text"]
                    if best_score == 0:
                        best_val = None

                if not best_val:
                    log.append(f"⚠ No portal match for: {raw_name}")
                    failed.append(raw_name)
                    continue

                log.append(f"Adding: {raw_name} → {best_text} (ID:{best_val}) × {qty}")

                # Select product
                page.select_option(SEL_PRODUCT, best_val)
                page.wait_for_timeout(2000)  # wait for price AJAX to load

                # Fill qty
                page.fill(SEL_QTY, str(qty))
                page.wait_for_timeout(300)

                # Click Add
                page.click(SEL_ADD)
                page.wait_for_timeout(2500)  # wait for row to appear in grid

                added.append({
                    "name":       raw_name,
                    "matched_as": best_text,
                    "portal_id":  best_val,
                    "qty":        qty,
                })

            if not added:
                browser.close()
                return {
                    "success": False,
                    "error":   "No items could be matched and added. Check product names.",
                    "failed":  failed,
                    "log":     log,
                }

            # ── 5. Click "Send For Approval" ─────────────────────────────────
            log.append(f"Submitting order ({len(added)} items)…")
            page.click(SEL_SAVE)
            page.wait_for_timeout(5000)
            log.append(f"Save clicked. Final URL: {page.url}")

            # Screenshot for confirmation
            ts = datetime.now().strftime("%H%M%S")
            ss_path = f"debug_stock_order_{ts}.png"
            page.screenshot(path=ss_path, full_page=True)
            log.append(f"Screenshot: {ss_path}")

            browser.close()

            return {
                "success":      True,
                "items_added":  added,
                "items_failed": failed,
                "log":          log,
                "submitted_at": datetime.now().isoformat(),
            }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error":   str(e),
            "detail":  traceback.format_exc(),
            "log":     log,
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Usage: python submit_stock_order.py '<json_items>'"}))
        sys.exit(1)
    try:
        items = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    result = submit_stock_order(items)
    print(json.dumps(result, ensure_ascii=False))
