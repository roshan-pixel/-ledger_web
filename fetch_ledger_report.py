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
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            
            page.evaluate('''() => {
                ["ctl00_ContentPlaceHolder1_txtspUserid","ctl00_ContentPlaceHolder1_txtsppassword"].forEach(id => {
                    let el = document.getElementById(id);
                    if (!el) return;
                    while (el && el !== document.body) { el.style.display = "block"; el = el.parentElement; }
                });
            }''')

            page.fill("input[name='ctl00$ContentPlaceHolder1$txtspUserid']", username, force=True)
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtsppassword']", password, force=True)
            
            # Submit and just wait for navigation commit
            with page.expect_navigation(wait_until="commit"):
                page.click("input[name='ctl00$ContentPlaceHolder1$btnfranlogin']", force=True)

            # ── 2. Go to Ledger Report ────────────────────────────────────────
            page.goto(LEDGER_URL, wait_until="domcontentloaded")

            from_date = "01/06/2026"
            to_date   = datetime.now().strftime("%d/%m/%Y")

            # ── 3. Fill date fields via JS (bypasses xdsoft date picker) ──────
            page.evaluate(f'''() => {{
                const from = document.querySelector("input[name='ctl00$ContentPlaceHolder1$txtfrom']");
                const to   = document.querySelector("input[name='ctl00$ContentPlaceHolder1$txtto']");
                if (from) {{ from.value = "{from_date}"; }}
                if (to)   {{ to.value   = "{to_date}"; }}
            }}''')

            # ── 4. Click Show ──────────────────────────────────────────────────
            # Click and wait for the table to refresh. 
            page.click("input[name='ctl00$ContentPlaceHolder1$Button1']")
            
            # Wait for lblbal to become visible OR just wait 3 seconds
            try:
                page.wait_for_selector("#ctl00_ContentPlaceHolder1_lblbal", state="attached", timeout=8000)
            except Exception:
                pass
            page.wait_for_timeout(1000)

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

            # ── 6. Parse the ledger table via JS (Instant!) ─────────────────────
            entries, headers = page.evaluate('''() => {
                const tables = document.querySelectorAll("table");
                let maxRows = 0;
                let ledgerTable = null;
                for (let t of tables) {
                    if (t.rows.length > maxRows) {
                        maxRows = t.rows.length;
                        ledgerTable = t;
                    }
                }
                
                if (!ledgerTable || maxRows <= 1) return [[], []];
                
                let headers = [];
                let entries = [];
                let headerRowIdx = -1;
                
                for (let i=0; i < ledgerTable.rows.length; i++) {
                    const row = ledgerTable.rows[i];
                    let cells = Array.from(row.cells).map(c => c.innerText.trim());
                    let textJoined = cells.join(" ").toLowerCase();
                    if (textJoined.includes("date") && (textJoined.includes("particular") || textJoined.includes("detail")) && textJoined.includes("balance")) {
                        headers = cells;
                        headerRowIdx = i;
                        break;
                    }
                }
                
                if (headerRowIdx !== -1) {
                    for (let i = headerRowIdx + 1; i < ledgerTable.rows.length; i++) {
                        const row = ledgerTable.rows[i];
                        let cells = Array.from(row.cells).map(c => c.innerText.trim());
                        if (cells.some(c => c)) { // not empty
                            let rowDict = {};
                            for (let j=0; j<headers.length; j++) {
                                rowDict[headers[j]] = cells[j] || "";
                            }
                            entries.push(rowDict);
                        }
                    }
                }
                
                return [entries, headers];
            }''')

            # Fallback: if closing_balance still 0, try the last row's balance column
            if closing_balance == 0.0 and entries:
                last = entries[-1]
                for key, val in last.items():
                    if "balance" in key.lower():
                        raw = re.sub(r'[^\d.]', '', str(val))
                        try:
                            closing_balance = float(raw)
                        except ValueError:
                            pass

            browser.close()

            result = {
                "success":         True,
                "from_date":       from_date,
                "to_date":         to_date,
                "franchise_value": "960158985",
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
