"""
init_ledger_table.py  –  one-time migration
Creates the ledger_report table and a wallet_balance settings key in ledger.db.
Run: python init_ledger_table.py
"""
import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "ledger.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Ledger entries table
c.execute("""
    CREATE TABLE IF NOT EXISTS ledger_report (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date  TEXT,
        particulars TEXT,
        debit       REAL DEFAULT 0,
        credit      REAL DEFAULT 0,
        balance     REAL DEFAULT 0,
        raw_row     TEXT,
        scraped_at  TEXT
    )
""")

# Upsert the wallet/closing balance into settings
c.execute("""
    INSERT OR IGNORE INTO settings (key, value)
    VALUES ('wallet_balance', '0')
""")
c.execute("""
    INSERT OR IGNORE INTO settings (key, value)
    VALUES ('ledger_scraped_at', '')
""")
c.execute("""
    INSERT OR IGNORE INTO settings (key, value)
    VALUES ('ledger_closing_balance', '0')
""")

conn.commit()
conn.close()
print("Done — ledger_report table ready.")
