import sqlite3
import json

invoices = [
    {
        "invoice_no": "DSR/000068/26-27",
        "ds_code": "378BBCE1",
        "customer_name": "LALHLIMPARI",
        "amount": 23715.00,
        "date_created": "08/07/2026",
        "items": [
            {"name": "LAVENDER SUNSREEN STICKBROAD SPECTURM SPF50 PA++++ [300]", "qty": 5, "price": 465.25, "total": 2326.25},
            {"name": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-CREAMY VANILLA [390]", "qty": 5, "price": 634.75, "total": 3173.75},
            {"name": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-SOFT BEIGE [391]", "qty": 5, "price": 634.75, "total": 3173.75},
            {"name": "LUMITOUCH COMPACT POWDER-BRIGHT LIGHT [410]", "qty": 5, "price": 592.37, "total": 2961.85},
            {"name": "POWDER BLUSH- COY [417]", "qty": 3, "price": 550.00, "total": 1650.00},
            {"name": "LUMITOUCH COMPACT POWDER RADIANT BEIGE [414]", "qty": 5, "price": 592.37, "total": 2961.85},
            {"name": "POWDER BLUSH- SEDUCTRESS [416]", "qty": 7, "price": 550.00, "total": 3850.00}
        ],
        "total_sp": 100.00,
        "status": "active"
    },
    {
        "invoice_no": "DSR/000069/26-27",
        "ds_code": "C5106F62",
        "customer_name": "VANLALRUATI",
        "amount": 5661.00,
        "date_created": "08/07/2026",
        "items": [
            {"name": "LIVODOC RAS [47]", "qty": 1, "price": 1227.21, "total": 1227.21},
            {"name": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-SILK ALMOND [392]", "qty": 1, "price": 634.75, "total": 634.75},
            {"name": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-WARM CHESTNUT [393]", "qty": 1, "price": 634.75, "total": 634.75},
            {"name": "LUMITOUCH COMPACT POWDER- BANANA EDGE [412]", "qty": 1, "price": 592.37, "total": 592.37},
            {"name": "LUMITOUCH COMPACT POWDER- CAPPUCCINO [413]", "qty": 1, "price": 592.37, "total": 592.37},
            {"name": "LUXE MATTE LIQUID LIPSTICK- CINNAMON [447]", "qty": 1, "price": 312.71, "total": 312.71},
            {"name": "LUXE MATTE LIQUID LIPSTICK- CARAMEL [448]", "qty": 1, "price": 312.71, "total": 312.71},
            {"name": "LUXE MATTE LIQUID LIPSTICK- CHOCO DELIGHT [452]", "qty": 1, "price": 312.71, "total": 312.71},
            {"name": "LUXE MATTE LIQUID LIPSTICK- ROSE PLAY [446]", "qty": 1, "price": 312.71, "total": 312.71}
        ],
        "total_sp": 26.00,
        "status": "active"
    },
    {
        "invoice_no": "DSR/000070/26-27",
        "ds_code": "4037B6D1",
        "customer_name": "MALSAWMTHANGI",
        "amount": 10131.00,
        "date_created": "08/07/2026",
        "items": [
            {"name": "GYNEDOC RAS [46]", "qty": 1, "price": 1184.71, "total": 1184.71},
            {"name": "BATHVEDA GOAT MILK BAR [237]", "qty": 4, "price": 261.86, "total": 1047.44},
            {"name": "BATHVEDA NEEM TULSI BAR [241]", "qty": 2, "price": 157.04, "total": 314.08},
            {"name": "COLLAGEN + PEPTIDE FACE SHEET [297]", "qty": 2, "price": 190.68, "total": 381.36},
            {"name": "AHA + BHA FACE SHEET MASK [295]", "qty": 2, "price": 190.68, "total": 381.36},
            {"name": "SALICYLIC ACID FACE SHEET MASK [294]", "qty": 2, "price": 190.68, "total": 381.36},
            {"name": "KOJIC ACID FACE SHEET MASK [296]", "qty": 2, "price": 190.68, "total": 381.36},
            {"name": "HAIR GROWTH SERUM [293]", "qty": 1, "price": 422.88, "total": 422.88},
            {"name": "SUNSCREEN SPF50 PA++++ GEL [299]", "qty": 1, "price": 244.92, "total": 244.92},
            {"name": "LAVENDER SUNSREEN STICKBROAD SPECTURM SPF50 PA++++ [300]", "qty": 1, "price": 465.25, "total": 465.25},
            {"name": "MATT EYE LINER BLACK [426]", "qty": 1, "price": 524.58, "total": 524.58},
            {"name": "LUXE MATTE LIQUID LIPSTICK- FINE WINE [442]", "qty": 3, "price": 312.71, "total": 938.13},
            {"name": "LUXE MATTE LIQUID LIPSTICK- ROSE PLAY [446]", "qty": 2, "price": 312.71, "total": 625.42},
            {"name": "LUXE MATTE LIQUID LIPSTICK- FIERY [450]", "qty": 2, "price": 312.71, "total": 625.42},
            {"name": "LUXE MATTE LIQUID LIPSTICK- HALEN [451]", "qty": 1, "price": 312.71, "total": 312.71},
            {"name": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-WARM CHESTNUT [393]", "qty": 1, "price": 634.75, "total": 634.75}
        ],
        "total_sp": 41.50,
        "status": "active"
    },
    {
        "invoice_no": "DSR/000071/26-27",
        "ds_code": "665CA518",
        "customer_name": "R LALCHHANHIMI",
        "amount": 6405.00,
        "date_created": "08/07/2026",
        "items": [
            {"name": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-SILK ALMOND [392]", "qty": 1, "price": 634.75, "total": 634.75},
            {"name": "ULTRA SMOOTH FOUNDATION FOR RADIANT GLOW-WARM CHESTNUT [393]", "qty": 1, "price": 634.75, "total": 634.75},
            {"name": "LUMITOUCH COMPACT POWDER- CAPPUCCINO [413]", "qty": 1, "price": 592.37, "total": 592.37},
            {"name": "COLOR DREW BLUSH STICK- FLIRTY [402]", "qty": 1, "price": 338.14, "total": 338.14},
            {"name": "MATT EYE LINER BLACK [426]", "qty": 3, "price": 524.58, "total": 1573.74},
            {"name": "EYELINER HOLOGRAPHIC- AMBRE GREEN FLARE [423]", "qty": 2, "price": 168.64, "total": 337.28},
            {"name": "BLURR LOOSE POWDER- BANANA PUNCH [406]", "qty": 1, "price": 753.39, "total": 753.39},
            {"name": "V SPLASH [349]", "qty": 3, "price": 211.02, "total": 633.06}
        ],
        "total_sp": 27.50,
        "status": "active"
    },
    {
        "invoice_no": "DSR/000072/26-27",
        "ds_code": "C5106F62",
        "customer_name": "VANLALRUATI",
        "amount": 206.00,
        "date_created": "08/07/2026",
        "items": [
            {"name": "DENTODOC CREAM [50]", "qty": 1, "price": 195.85, "total": 195.85}
        ],
        "total_sp": 1.00,
        "status": "active"
    }
]

db_path = 'C:/Users/sgarm/Downloads/ledger_web/ledger.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

for inv in invoices:
    c.execute("SELECT id FROM invoices WHERE invoice_no = ?", (inv['invoice_no'],))
    existing = c.fetchone()
    if not existing:
        c.execute('''INSERT INTO invoices (invoice_no, ds_code, customer_name, amount, date_created, items, status, total_sp)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (inv['invoice_no'], inv['ds_code'], inv['customer_name'], inv['amount'], 
                   inv['date_created'], json.dumps(inv['items']), inv['status'], inv['total_sp']))

conn.commit()
conn.close()
print("Successfully added invoices.")
