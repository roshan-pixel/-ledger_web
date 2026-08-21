"""
fetch_ledger_report.py  –  Precise multi-page scraper for SpLedgerReport.aspx
Logs into Asclepius portal, fills date range, clicks Show, scrapes all
paginated pages (Page 1, 2, 3, etc.) and closing balance.

Usage:
  python fetch_ledger_report.py <username> <password> [from_date] [to_date]

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


def fetch_ledger_report(username: str, password: str, from_date: str = "01/01/2025", to_date: str = None) -> dict:
    if not to_date:
        to_date = datetime.now().strftime("%d/%m/%Y")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            # ── 1. Login ────────────────────────────────────────────────────
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            
            page.evaluate("""() => {
                ["ctl00_ContentPlaceHolder1_txtspUserid","ctl00_ContentPlaceHolder1_txtsppassword"].forEach(id => {
                    let el = document.getElementById(id);
                    if (!el) return;
                    while (el && el !== document.body) { el.style.display = "block"; el = el.parentElement; }
                });
            }""")

            page.fill("input[name='ctl00$ContentPlaceHolder1$txtspUserid']", username, force=True)
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtsppassword']", password, force=True)
            
            # Submit login
            page.click("input[name='ctl00$ContentPlaceHolder1$btnfranlogin']", force=True)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

            # ── 2. Go to Ledger Report ────────────────────────────────────────
            page.goto(LEDGER_URL, wait_until="networkidle")
            page.wait_for_timeout(1000)

            # ── 3. Fill date fields via JS (bypasses date picker popup) ──────
            page.evaluate(f"""() => {{
                const from = document.querySelector("input[name='ctl00$ContentPlaceHolder1$txtfrom']");
                const to   = document.querySelector("input[name='ctl00$ContentPlaceHolder1$txtto']");
                if (from) {{{{ from.value = "{from_date}"; }}}}
                if (to)   {{{{ to.value   = "{to_date}"; }}}}
            }}""")

            # ── 4. Click Show ──────────────────────────────────────────
            page.click("input[name='ctl00$ContentPlaceHolder1$Button1']")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # ── 5. Extract closing balance label if available ─────────────────
            balance_text = ""
            try:
                bal_el = page.locator("#ctl00_ContentPlaceHolder1_lblbal")
                if bal_el.count() > 0:
                    balance_text = bal_el.inner_text().strip()
            except Exception as e:
                print(f"[warn] lblbal query error: {e}", file=sys.stderr)

            # ── 6. Multi-Page Extraction Loop ─────────────────────────────────
            all_entries = []
            headers = []
            visited_pages = set()
            max_pages = 50  # safety cap
            page_counter = 0

            while page_counter < max_pages:
                page_counter += 1

                page_data = page.evaluate("""() => {
                    let table = document.querySelector("#ctl00_ContentPlaceHolder1_gv_data");
                    if (!table) {
                        const tables = document.querySelectorAll("table");
                        let maxRows = 0;
                        for (let t of tables) {
                            if (t.rows.length > maxRows) {
                                maxRows = t.rows.length;
                                table = t;
                            }
                        }
                    }
                    
                    if (!table || table.rows.length <= 1) {
                        return { headers: [], rows: [], pages: [], currentPage: null };
                    }
                    
                    let headers = [];
                    let headerRowIdx = -1;
                    
                    for (let i = 0; i < table.rows.length; i++) {
                        const row = table.rows[i];
                        let cells = Array.from(row.cells).map(c => c.innerText.trim());
                        let textJoined = cells.join(" ").toLowerCase();
                        if (textJoined.includes("date") && (textJoined.includes("particular") || textJoined.includes("detail")) && textJoined.includes("balance")) {
                            headers = cells;
                            headerRowIdx = i;
                            break;
                        }
                    }
                    
                    if (headerRowIdx === -1) {
                        headers = Array.from(table.rows[0].cells).map(c => c.innerText.trim());
                        headerRowIdx = 0;
                    }
                    
                    let rows = [];
                    let pages = [];
                    let currentPage = null;
                    
                    for (let i = headerRowIdx + 1; i < table.rows.length; i++) {
                        const row = table.rows[i];
                        const isPager = row.classList.contains("cssPager") || !!row.querySelector("table") || !!row.querySelector("a[href*='Page$']");
                        
                        if (isPager) {
                            const spans = row.querySelectorAll("span");
                            for (let s of spans) {
                                let txt = s.innerText.trim();
                                if (!isNaN(txt) && parseInt(txt) > 0) {
                                    currentPage = parseInt(txt);
                                }
                            }
                            
                            const links = row.querySelectorAll("a");
                            for (let a of links) {
                                let txt = a.innerText.trim();
                                let href = a.getAttribute("href") || "";
                                let match = href.match(/Page\$(\d+)/) || txt.match(/(\d+)/);
                                let targetPage = match ? parseInt(match[1]) : (txt === "..." ? "next_set" : txt);
                                pages.push({
                                    text: txt,
                                    targetPage: targetPage,
                                    href: href
                                });
                            }
                        } else {
                            let cells = Array.from(row.cells).map(c => c.innerText.trim());
                            if (cells.some(c => c)) {
                                let rowDict = {};
                                for (let j = 0; j < headers.length; j++) {
                                    rowDict[headers[j]] = cells[j] || "";
                                }
                                rows.push(rowDict);
                            }
                        }
                    }
                    
                    return {
                        headers: headers,
                        rows: rows,
                        pages: pages,
                        currentPage: currentPage
                    };
                }""")

                cur_p = page_data.get("currentPage") or page_counter
                if not headers and page_data.get("headers"):
                    headers = page_data["headers"]

                if cur_p in visited_pages:
                    break

                visited_pages.add(cur_p)
                all_entries.extend(page_data.get("rows", []))

                available_pages = page_data.get("pages", [])
                next_target = None

                for p_info in available_pages:
                    tp = p_info.get("targetPage")
                    if isinstance(tp, int) and tp not in visited_pages and tp > cur_p:
                        next_target = p_info
                        break

                if not next_target:
                    for p_info in available_pages:
                        tp = p_info.get("targetPage")
                        if isinstance(tp, int) and tp not in visited_pages:
                            next_target = p_info
                            break

                if not next_target:
                    for p_info in available_pages:
                        if p_info.get("text") == "..." or p_info.get("targetPage") == "next_set":
                            next_target = p_info
                            break

                if not next_target:
                    break

                target_text = next_target.get("text", "")
                target_href = next_target.get("href", "")

                try:
                    pager_link_selector = f"#ctl00_ContentPlaceHolder1_gv_data tr.cssPager a:has-text('{target_text}')"
                    if page.locator(pager_link_selector).count() > 0:
                        page.click(pager_link_selector)
                    elif target_href:
                        page.evaluate(target_href)
                    else:
                        break

                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"[warn] Error navigating to page {target_text}: {e}", file=sys.stderr)
                    break

            # ── 7. Deduplicate entries while preserving order ────────────────
            seen_entries = set()
            deduped_entries = []
            for entry in all_entries:
                sno = entry.get("Sno") or entry.get("S.No") or entry.get("SNo") or ""
                dt  = entry.get("Transaction Date") or entry.get("Date") or ""
                amt = entry.get("Transaction Amount") or entry.get("Amount") or ""
                bal = entry.get("Balance") or ""
                key = (sno, dt, amt, bal)
                if key not in seen_entries:
                    seen_entries.add(key)
                    deduped_entries.append(entry)

            try:
                deduped_entries.sort(key=lambda x: int(re.sub(r"\D", "", str(x.get("Sno") or x.get("S.No") or "0")) or 0))
            except Exception:
                pass

            # ── 8. Calculate Closing Balance ─────────────────────────────────
            closing_balance = 0.0
            if balance_text:
                m = re.search(r"[\d,]+\.?\d*", balance_text)
                if m:
                    closing_balance = float(m.group(0).replace(",", ""))

            if closing_balance == 0.0 and deduped_entries:
                last = deduped_entries[-1]
                for key, val in last.items():
                    if "balance" in key.lower():
                        raw = re.sub(r"[^\d.]", "", str(val))
                        try:
                            closing_balance = float(raw)
                            break
                        except ValueError:
                            pass

            browser.close()

            result = {
                "success":         True,
                "from_date":       from_date,
                "to_date":         to_date,
                "franchise_value": "960158985",
                "headers":         headers,
                "entries":         deduped_entries,
                "closing_balance": closing_balance,
                "balance_text":    balance_text,
                "scraped_at":      datetime.now().isoformat(),
                "row_count":       len(deduped_entries),
                "pages_scraped":   len(visited_pages)
            }

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
        print(json.dumps({"success": False, "error": "Usage: python fetch_ledger_report.py <username> <password> [from_date] [to_date]"}))
        sys.exit(1)
    
    u = sys.argv[1]
    p = sys.argv[2]
    from_d = sys.argv[3] if len(sys.argv) > 3 else "01/01/2025"
    to_d   = sys.argv[4] if len(sys.argv) > 4 else None

    result = fetch_ledger_report(u, p, from_d, to_d)
    print(json.dumps(result, ensure_ascii=False))
