"""
fetch_ledger_report.py  –  Precise scraper for SpLedgerReport.aspx
Logs into Asclepius portal, fills from=01/01/2026 to=today,
clicks Show, scrapes the table and closing balance (lblbal).

Usage:
  python fetch_ledger_report.py <username> <password>

Output:
  JSON to STDOUT + writes ledger_report.json
"""

import json
import sys
import re
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "ledger_report.json")

LEDGER_URL = "https://asclepiuswellness.com/shoppingpoint/SpLedgerReport.aspx"
LOGIN_URL  = "https://asclepiuswellness.com/login.aspx?webid=1"


def fetch_ledger_report(username: str, password: str) -> dict:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            # ── 1. Login ──────────────────────────────────────────────────────
            page.goto(LOGIN_URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

            # Reveal hidden ASP.NET fields
            page.evaluate('''() => {
                ["ctl00_ContentPlaceHolder1_txtspUserid","ctl00_ContentPlaceHolder1_txtsppassword"].forEach(id => {
                    let el = document.getElementById(id);
                    if (!el) return;
                    while (el && el !== document.body) { el.style.display = "block"; el = el.parentElement; }
                });
            }''')

            page.fill("input[name='ctl00$ContentPlaceHolder1$txtspUserid']", username, force=True)
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtsppassword']", password, force=True)
            page.click("input[name='ctl00$ContentPlaceHolder1$btnfranlogin']", force=True)

            try:
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(2000)
            except Exception:
                pass

            # ── 2. Go to Ledger Report ────────────────────────────────────────
            page.goto(LEDGER_URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            from_date = "01/01/2026"
            to_date   = datetime.now().strftime("%d/%m/%Y")

            # ── 3. Fill date fields via JS (bypasses xdsoft date picker) ──────
            page.evaluate(f'''() => {{
                const from = document.querySelector("input[name='ctl00$ContentPlaceHolder1$txtfrom']");
                const to   = document.querySelector("input[name='ctl00$ContentPlaceHolder1$txtto']");
                if (from) {{ from.value = "{from_date}"; }}
                if (to)   {{ to.value   = "{to_date}"; }}
            }}''')
            page.wait_for_timeout(500)

            # Make sure the franchise dropdown has the pre-selected franchise value
            # (It's already pre-selected from the page load, but let's confirm)
            franchise_value = page.eval_on_selector(
                "select[name='ctl00$ContentPlaceHolder1$ddlfranch']",
                "el => el.value"
            )

            # ── 4. Click Show ──────────────────────────────────────────────────
            page.click("input[name='ctl00$ContentPlaceHolder1$Button1']")
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(3000)
            except Exception:
                page.wait_for_timeout(3000)

            # ── 5. Extract closing balance from lblbal ─────────────────────────
            balance_text = ""
            closing_balance = 0.0
            try:
                balance_text = page.locator("#ctl00_ContentPlaceHolder1_lblbal").inner_text()
                # e.g. "Closing Balance : 12,345.67" or just "12,345.67"
                m = re.search(r'[\d,]+\.?\d*', balance_text)
                if m:
                    closing_balance = float(m.group(0).replace(',', ''))
            except Exception as e:
                print(f"[warn] lblbal not found: {e}", file=sys.stderr)

            # ── 6. Parse the ledger table ──────────────────────────────────────
            from bs4 import BeautifulSoup
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            # Find the main data table – pick the one with most data rows
            tables = soup.find_all("table")
            ledger_table = None
            max_rows = 0
            for t in tables:
                rows = t.find_all("tr")
                if len(rows) > max_rows:
                    max_rows = len(rows)
                    ledger_table = t

            entries = []
            headers = []

            if ledger_table and max_rows > 1:
                rows = ledger_table.find_all("tr")
                header_row_idx = None

                # Find header row
                for i, row in enumerate(rows):
                    ths = row.find_all("th")
                    tds = row.find_all("td")
                    cells = ths if ths else tds
                    cell_texts = [c.get_text(strip=True) for c in cells]
                    text_joined = " ".join(cell_texts).lower()
                    if any(kw in text_joined for kw in ["date", "particular", "debit", "credit", "balance"]):
                        headers = cell_texts
                        header_row_idx = i
                        break

                if header_row_idx is not None:
                    for row in rows[header_row_idx + 1:]:
                        cells = row.find_all("td")
                        cell_texts = [c.get_text(strip=True) for c in cells]
                        if not any(t.strip() for t in cell_texts):
                            continue
                        if len(cell_texts) >= 2:
                            row_dict = {}
                            for j, h in enumerate(headers):
                                row_dict[h] = cell_texts[j] if j < len(cell_texts) else ""
                            entries.append(row_dict)

            # Fallback: if closing_balance still 0, try the last row's balance column
            if closing_balance == 0.0 and entries:
                last = entries[-1]
                for key, val in last.items():
                    if "balance" in key.lower():
                        raw = re.sub(r'[^\d.]', '', val)
                        try:
                            closing_balance = float(raw)
                        except ValueError:
                            pass

            browser.close()

            result = {
                "success":         True,
                "from_date":       from_date,
                "to_date":         to_date,
                "franchise_value": franchise_value,
                "headers":         headers,
                "entries":         entries,
                "closing_balance": closing_balance,
                "balance_text":    balance_text,
                "scraped_at":      datetime.now().isoformat(),
                "row_count":       len(entries),
            }

            # Persist to file for fast serving
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            return result

    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        return {
            "success":         False,
            "error":           str(e),
            "detail":          err_detail,
            "entries":         [],
            "closing_balance": 0.0,
        }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Usage: python fetch_ledger_report.py <username> <password>"}))
        sys.exit(1)
    result = fetch_ledger_report(sys.argv[1], sys.argv[2])
    print(json.dumps(result, ensure_ascii=False))
