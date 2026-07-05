import sqlite3
import json
import re

# Parse SP data
sp_map = {}
with open('sp_data.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        # Example format: 1 109 EYEDOC DROP 1128.00 7.00 7.00
        # Wait, there are spaces in the product name.
        # Match using regex: digits at the end are DP SP RSP
        match = re.search(r'(.*?)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)$', line)
        if match:
            # name might have leading numbers (S.NO Product Code)
            prefix = match.group(1).strip()
            # remove leading digits which are S.NO and Product Code
            prefix_match = re.search(r'^\d+\s+\d+\s+(.*)$', prefix)
            if prefix_match:
                name = prefix_match.group(1).strip().upper()
                sp = float(match.group(3))
                sp_map[name] = sp

print(f"Loaded {len(sp_map)} products from SP data.")

# Connect to db
conn = sqlite3.connect('ledger.db')
c = conn.cursor()

# Update headers
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
row = c.fetchone()
headers = json.loads(row[0])

print(f"Current headers: {len(headers)}")

# Let's put SP/Pc at index 26 and Total SP at index 27
if headers[26] == "": headers[26] = "SP/Pc"
if headers[27] == "": headers[27] = "Total SP"

c.execute("UPDATE settings SET value=? WHERE key='inventory_headers'", (json.dumps(headers),))

# Now update inventory table
c.execute("SELECT row_num, c3 FROM inventory WHERE UPPER(c3) != 'TOTAL' AND c3 IS NOT NULL AND c3 != ''")
rows = c.fetchall()

updated_count = 0
for row in rows:
    row_num, raw_name = row
    # Clean name: usually looks like "JOINT CURATOR OIL [4] -" or similar
    # Remove anything after '['
    clean_name = raw_name.split('[')[0].strip().upper()
    
    # Try exact match first
    sp = sp_map.get(clean_name, None)
    
    # Try fuzzy match if not found
    if sp is None:
        for map_name in sp_map:
            if map_name in clean_name or clean_name in map_name:
                sp = sp_map[map_name]
                break

    if sp is not None:
        c.execute("UPDATE inventory SET c27=? WHERE row_num=?", (sp, row_num))
        updated_count += 1
    else:
        print(f"SP not found for: {raw_name} (clean: {clean_name})")

conn.commit()
print(f"Updated {updated_count} rows with SP/Pc.")

# Now update Total SP (which would be SP/Pc * Remaining Qty)
# Remaining Qty is at c19
c.execute("UPDATE inventory SET c28 = CAST(c19 AS REAL) * CAST(c27 AS REAL) WHERE c19 != '' AND c27 != '' AND c27 IS NOT NULL AND UPPER(c3) != 'TOTAL'")
conn.commit()

# Update the TOTAL row
c.execute("SELECT SUM(CAST(c28 AS REAL)) FROM inventory WHERE c28 != '' AND UPPER(c3) != 'TOTAL'")
total_sp = c.fetchone()[0]
if total_sp is not None:
    c.execute("UPDATE inventory SET c28 = ? WHERE UPPER(c3) = 'TOTAL'", (total_sp,))
    conn.commit()
    print(f"Updated Total SP to {total_sp}")

conn.close()
