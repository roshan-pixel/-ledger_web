"""
submit_stock_order.py  –  Submits a Stock Point Order to the Asclepius portal.

The franchise (DSR 7 WELLNESS CENTRE) places a purchase order to AWPL via:
  https://asclepiuswellness.com/shoppingpoint/SpPurchaseOrder.aspx

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

LOGIN_URL  = "https://asclepiuswellness.com/login.aspx?webid=1"
ORDER_URL  = "https://asclepiuswellness.com/shoppingpoint/SpPurchaseOrder.aspx"

USERNAME = "AAZFD8117G"
PASSWORD = "ABC@1234"


def submit_stock_order(items: list) -> dict:
    """
    items: list of dicts with keys: name, qty (total pieces), portal_id (optional)
    """
    log = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            # Auto-accept all JS dialogs (confirmation popups on Save)
            def handle_dialog(dialog):
                log.append(f"[PORTAL DIALOG] {dialog.message}")
                dialog.accept()
            page.on("dialog", handle_dialog)

            # ── 1. Login ──────────────────────────────────────────────────────
            log.append("Navigating to login page…")
            page.goto(LOGIN_URL, wait_until="networkidle")
            page.wait_for_timeout(1500)

            page.fill("input[name='ctl00$ContentPlaceHolder1$txtspUserid']", USERNAME, force=True)
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtsppassword']", PASSWORD, force=True)
            page.click("input[name='ctl00$ContentPlaceHolder1$btnfranlogin']", force=True)
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(1500)
            log.append("Logged in successfully.")

            # ── 2. Go to Purchase Order page ──────────────────────────────────
            log.append(f"Navigating to purchase order page: {ORDER_URL}")
            page.goto(ORDER_URL, wait_until="networkidle")
            page.wait_for_timeout(2000)

            # ── 3. Get available items from the product dropdown ───────────────
            # The page likely has a product select dropdown
            # Try common field names used by Asclepius portal
            product_selector = None
            for sel in [
                "#ctl00_ContentPlaceHolder1_itemlist",
                "#ctl00_ContentPlaceHolder1_ddlItem",
                "#ctl00_ContentPlaceHolder1_ddlProduct",
                "select[name*='itemlist']",
                "select[name*='Item']",
                "select[name*='Product']",
            ]:
                try:
                    count = page.locator(sel).count()
                    if count > 0:
                        product_selector = sel
                        log.append(f"Found product dropdown: {sel}")
                        break
                except Exception:
                    pass

            if not product_selector:
                # Take a screenshot to diagnose
                page.screenshot(path="debug_stock_order_page.png", full_page=True)
                # Save page HTML for inspection
                html = page.content()
                with open("debug_stock_order_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
                browser.close()
                return {
                    "success": False,
                    "error": "Could not find product dropdown on the purchase order page. Screenshot saved.",
                    "log": log,
                    "page_url": page.url,
                }

            # Get all available options
            options = page.evaluate(f'''() => {{
                return Array.from(document.querySelectorAll('{product_selector} option')).map(o => ({{
                    val: o.value, text: o.text.trim()
                }}));
            }}''')
            # Remove blank/select placeholder
            options = [o for o in options if o['val'] and 'select' not in o['text'].lower()]
            log.append(f"Found {len(options)} products in dropdown.")

            # Find qty/add button selectors
            qty_selector = None
            for sel in [
                "#ctl00_ContentPlaceHolder1_txtqty",
                "#ctl00_ContentPlaceHolder1_txtQty",
                "input[name*='txtqty']",
                "input[name*='Qty']",
            ]:
                if page.locator(sel).count() > 0:
                    qty_selector = sel
                    break

            add_btn_selector = None
            for sel in [
                "#ctl00_ContentPlaceHolder1_btnadd",
                "#ctl00_ContentPlaceHolder1_btnAdd",
                "input[name*='btnadd']",
                "input[value='Add']",
                "input[value='ADD']",
            ]:
                if page.locator(sel).count() > 0:
                    add_btn_selector = sel
                    break

            # ── 4. Add each item ──────────────────────────────────────────────
            added = []
            failed = []

            for item in items:
                item_name = item.get("name", "").strip().upper()
                qty = int(item.get("qty", 0))
                portal_id = str(item.get("portal_id", "")).strip()

                if not item_name or qty <= 0:
                    continue

                # Find matching option
                best_match = None

                # Try by portal_id first (most reliable)
                if portal_id:
                    for opt in options:
                        if opt['val'] == portal_id:
                            best_match = opt['val']
                            break

                # Fallback: fuzzy text match
                if not best_match:
                    item_words = set(item_name.split())
                    best_score = 0
                    for opt in options:
                        opt_upper = opt['text'].upper()
                        # Count matching words
                        score = sum(1 for w in item_words if w in opt_upper)
                        if score > best_score:
                            best_score = score
                            best_match = opt['val']

                if not best_match:
                    log.append(f"⚠ Could not find portal match for: {item_name}")
                    failed.append(item_name)
                    continue

                matched_name = next((o['text'] for o in options if o['val'] == best_match), best_match)
                log.append(f"Adding: {item_name} → {matched_name} (ID:{best_match}) × {qty}")

                # Select product
                page.select_option(product_selector, best_match)
                page.wait_for_timeout(2000)  # Wait for price/details to load via AJAX

                # Fill qty
                if qty_selector:
                    page.fill(qty_selector, str(qty))
                else:
                    # Try JS approach
                    page.evaluate(f"document.querySelector('input[name*=\"qty\"]').value = '{qty}'")

                page.wait_for_timeout(500)

                # Click Add
                if add_btn_selector:
                    page.click(add_btn_selector)
                    page.wait_for_timeout(2500)
                    added.append({"name": item_name, "qty": qty, "matched_as": matched_name})
                else:
                    log.append(f"⚠ No Add button found — skipping {item_name}")
                    failed.append(item_name)

            if not added:
                browser.close()
                return {
                    "success": False,
                    "error": "No items could be added to the order. Please check product names.",
                    "failed": failed,
                    "log": log,
                }

            # ── 5. Save / Submit the order ────────────────────────────────────
            log.append("Saving order to portal…")
            save_selector = None
            for sel in [
                "#ctl00_ContentPlaceHolder1_ButtonSave1",
                "#ctl00_ContentPlaceHolder1_btnSave",
                "input[value*='Save']",
                "input[value*='SAVE']",
                "input[value*='Submit']",
            ]:
                if page.locator(sel).count() > 0:
                    save_selector = sel
                    break

            if save_selector:
                page.click(save_selector)
                page.wait_for_timeout(4000)
            else:
                log.append("⚠ Save button not found — order may not be submitted")

            # Take confirmation screenshot
            screenshot_path = f"debug_stock_order_{datetime.now().strftime('%H%M%S')}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            log.append(f"Screenshot saved: {screenshot_path}")

            # Check for success indicators
            page_text = page.inner_text("body")
            order_success = any(kw in page_text.lower() for kw in [
                "order", "success", "saved", "submitted", "approved", "confirmed"
            ])

            browser.close()

            return {
                "success": True,
                "order_placed": order_success,
                "items_added": added,
                "items_failed": failed,
                "log": log,
                "submitted_at": datetime.now().isoformat(),
            }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "detail": traceback.format_exc(),
            "log": log,
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
