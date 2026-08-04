"""
monthly_rollover.py
────────────────────────────────────────────────────────────
Automatic monthly header rollover for the inventory system.

Detects the month that is currently stored in inventory_headers
(e.g. "Sold Qty (Jul 1-7)") and compares it to today's month.
If they differ, it rolls the headers over to the current month,
zeroes out the sold-qty columns for the new month, and re-sums
the TOTAL row — all with a single call: check_and_rollover(conn).

Can also be run directly:
    python monthly_rollover.py
"""

import calendar
import datetime
import json
import re
import sqlite3
from pathlib import Path

# Month abbreviation → month number
_MONTH_ABBR = {v: k for k, v in enumerate(
    ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
)}

DB_PATH = str(Path(__file__).parent / 'ledger.db')


def _get_header_month(headers):
    """
    Read the month that the Sold Qty columns are currently set to.
    Returns a (year, month_int, month_abbr) tuple, or None if not found.
    """
    for h in headers:
        m = re.search(r'Sold Qty \(([A-Za-z]{3})\s', str(h))
        if m:
            abbr = m.group(1)
            mon_num = _MONTH_ABBR.get(abbr)
            if mon_num:
                # Figure out the year: assume current or previous year
                now = datetime.date.today()
                year = now.year
                # If month > current month it must be last year
                if mon_num > now.month:
                    year -= 1
                return year, mon_num, abbr
    return None


def _build_week_ranges(days_in_month):
    return ["1-7", "8-14", "15-21", "22-28", f"29-{days_in_month}"]


def check_and_rollover(conn, verbose=True):
    """
    Check whether the inventory_headers month matches the current calendar
    month.  If not, roll over to the current month automatically.

    Accepts an open sqlite3 connection (row_factory = sqlite3.Row).
    Returns True if a rollover was performed, False if already current.
    """
    c = conn.cursor()

    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    row = c.fetchone()
    if not row:
        if verbose:
            print("[Rollover] inventory_headers not found in settings — skipping.")
        return False

    headers = json.loads(row[0])
    header_month = _get_header_month(headers)
    if header_month is None:
        if verbose:
            print("[Rollover] No dated Sold Qty headers found — nothing to roll.")
        return False

    hdr_year, hdr_mon, hdr_abbr = header_month
    today = datetime.date.today()

    if hdr_year == today.year and hdr_mon == today.month:
        if verbose:
            print(f"[Rollover] Headers already current ({hdr_abbr} {hdr_year}) — no rollover needed.")
        return False

    # ── Need to roll over ──────────────────────────────────────────────────
    new_year  = today.year
    new_mon   = today.month
    new_abbr  = today.strftime('%b')          # e.g. "Aug"
    days      = calendar.monthrange(new_year, new_mon)[1]
    week_ranges = _build_week_ranges(days)

    if verbose:
        print(f"[Rollover] Rolling headers from {hdr_abbr} → {new_abbr} {new_year}")

    qty_idx = val_idx = 0
    new_headers = []
    for h in headers:
        hs = str(h)
        if re.match(r'Sold Qty \([A-Za-z]{3}\s', hs):
            new_headers.append(f'Sold Qty ({new_abbr} {week_ranges[min(qty_idx, 4)]})')
            qty_idx += 1
        elif re.match(r'Sale Value \([A-Za-z]{3}\s', hs):
            new_headers.append(f'Sale Value ({new_abbr} {week_ranges[min(val_idx, 4)]})')
            val_idx += 1
        else:
            new_headers.append(h)

    # Persist new headers
    c.execute("UPDATE settings SET value=? WHERE key='inventory_headers'",
              (json.dumps(new_headers),))

    # Zero out the Sold Qty columns so the new month starts clean
    sold_cols = [i + 1 for i, h in enumerate(new_headers)
                 if re.match(r'Sold Qty \(', str(h))]
    for col_idx in sold_cols:
        c.execute(f"UPDATE inventory SET c{col_idx}=0 "
                  f"WHERE UPPER(TRIM(c3)) != 'TOTAL'")

    # Re-sum the TOTAL row
    c.execute("SELECT row_num FROM inventory WHERE UPPER(TRIM(c3)) = 'TOTAL'")
    tot = c.fetchone()
    if tot:
        cols_to_sum = list(range(6, 21)) + [28]
        sums = {}
        for ci in cols_to_sum:
            c.execute(f"SELECT SUM(CAST(REPLACE(COALESCE(c{ci},'0'),',','') AS REAL)) "
                      f"FROM inventory WHERE UPPER(TRIM(c3)) != 'TOTAL'")
            sums[f"c{ci}"] = c.fetchone()[0] or 0
        updates = ", ".join(f"{k}=?" for k in sums)
        c.execute(f"UPDATE inventory SET {updates} WHERE row_num=?",
                  (*sums.values(), tot['row_num']))

    conn.commit()
    if verbose:
        print(f"[Rollover] ✓ Headers rolled to {new_abbr} {new_year}. "
              f"Sold Qty columns zeroed: {sold_cols}")
    return True


# ── Run directly ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rolled = check_and_rollover(conn, verbose=True)
    conn.close()
    if not rolled:
        print("No rollover was needed — already on the current month.")
