import gspread
from gspread_formatting import *
import os

def format_sheet():
    creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
    gc = gspread.service_account(filename=creds_path)
    sheet = gc.open('MIZORAM BRONZA - 2026')
    ws = sheet.worksheet('Sheet1')
    
    data = ws.get_all_values()
    num_rows = len(data)
    
    print(f"Sheet has {num_rows} rows. Formatting...")
    
    # ── 1. FREEZE header row ──────────────────────────────────
    set_frozen(ws, rows=1)
    
    # ── 2. Column widths ──────────────────────────────────────
    # A=DS ID, B=DS Name, C=Bronze Comm, D=Bronze?, E=Bronze Date,
    # F=Silver Comm, G=Silver?, H=Silver Date,
    # I=Gold Comm, J=Gold?, K=Gold Date,
    # L=Plat Comm, M=Plat?, N=Plat Date, O=Phone
    col_widths = {
        'A': 120, 'B': 220, 'C': 130, 'D': 120, 'E': 130,
        'F': 130, 'G': 120, 'H': 130, 'I': 110, 'J': 110,
        'K': 130, 'L': 130, 'M': 120, 'N': 130, 'O': 140,
    }
    requests = []
    for col_letter, width in col_widths.items():
        col_index = ord(col_letter) - ord('A')
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": ws.id,
                    "dimension": "COLUMNS",
                    "startIndex": col_index,
                    "endIndex": col_index + 1
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize"
            }
        })
    
    # ── 3. Row heights ─────────────────────────────────────────
    requests.append({
        "updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 50},
            "fields": "pixelSize"
        }
    })
    requests.append({
        "updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "ROWS", "startIndex": 1, "endIndex": num_rows},
            "properties": {"pixelSize": 36},
            "fields": "pixelSize"
        }
    })
    
    sheet.batch_update({"requests": requests})
    print("Column widths and row heights set.")
    
    # ── 4. Header formatting ───────────────────────────────────
    header_base = CellFormat(
        textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(1, 1, 1)),
        horizontalAlignment='CENTER',
        verticalAlignment='MIDDLE',
        wrapStrategy='CLIP',
    )
    
    # DS ID & DS Name header - dark navy
    fmt_base_hdr = CellFormat(
        backgroundColor=Color(0.13, 0.17, 0.28),
        textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(1, 1, 1)),
        horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
    )
    # Bronze - warm brown
    fmt_bronze_hdr = CellFormat(
        backgroundColor=Color(0.5, 0.28, 0.08),
        textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(1, 0.95, 0.85)),
        horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
    )
    # Silver - steel blue-grey
    fmt_silver_hdr = CellFormat(
        backgroundColor=Color(0.27, 0.35, 0.45),
        textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(0.9, 0.94, 1)),
        horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
    )
    # Gold - rich gold
    fmt_gold_hdr = CellFormat(
        backgroundColor=Color(0.55, 0.40, 0.02),
        textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(1, 0.95, 0.65)),
        horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
    )
    # Platinum - deep purple-grey
    fmt_plat_hdr = CellFormat(
        backgroundColor=Color(0.25, 0.20, 0.38),
        textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(0.92, 0.88, 1)),
        horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
    )
    # Phone - dark
    fmt_phone_hdr = CellFormat(
        backgroundColor=Color(0.13, 0.17, 0.28),
        textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(1, 1, 1)),
        horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
    )
    
    format_cell_range(ws, 'A1:B1', fmt_base_hdr)
    format_cell_range(ws, 'C1:E1', fmt_bronze_hdr)
    format_cell_range(ws, 'F1:H1', fmt_silver_hdr)
    format_cell_range(ws, 'I1:K1', fmt_gold_hdr)
    format_cell_range(ws, 'L1:N1', fmt_plat_hdr)
    format_cell_range(ws, 'O1',    fmt_phone_hdr)
    print("Header colors applied.")
    
    # ── 5. Data row formatting ─────────────────────────────────
    if num_rows > 1:
        # Alternate row coloring
        light_row = CellFormat(
            backgroundColor=Color(0.97, 0.97, 0.98),
            textFormat=TextFormat(fontSize=10),
            verticalAlignment='MIDDLE',
        )
        dark_row = CellFormat(
            backgroundColor=Color(0.93, 0.94, 0.96),
            textFormat=TextFormat(fontSize=10),
            verticalAlignment='MIDDLE',
        )
        for row_i in range(2, num_rows + 1):
            fmt = light_row if row_i % 2 == 0 else dark_row
            format_cell_range(ws, f'A{row_i}:O{row_i}', fmt)
        
        # DS ID - bold, dark
        format_cell_range(ws, f'A2:A{num_rows}', CellFormat(
            textFormat=TextFormat(bold=True, fontSize=10, foregroundColor=Color(0.1, 0.15, 0.3)),
            horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
        ))
        # DS Name - bold
        format_cell_range(ws, f'B2:B{num_rows}', CellFormat(
            textFormat=TextFormat(bold=True, fontSize=10),
            verticalAlignment='MIDDLE',
        ))
        # Commission columns - right aligned, bold number
        for col in ['C', 'F', 'I', 'L']:
            format_cell_range(ws, f'{col}2:{col}{num_rows}', CellFormat(
                textFormat=TextFormat(bold=True, fontSize=10),
                horizontalAlignment='RIGHT', verticalAlignment='MIDDLE',
            ))
        # Achieved columns - centered
        for col in ['D', 'G', 'J', 'M']:
            format_cell_range(ws, f'{col}2:{col}{num_rows}', CellFormat(
                horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
            ))
        # Date columns - centered
        for col in ['E', 'H', 'K', 'N']:
            format_cell_range(ws, f'{col}2:{col}{num_rows}', CellFormat(
                horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
                textFormat=TextFormat(fontSize=9),
            ))
        # Phone - right aligned
        format_cell_range(ws, f'O2:O{num_rows}', CellFormat(
            horizontalAlignment='RIGHT', verticalAlignment='MIDDLE',
            textFormat=TextFormat(fontSize=10),
        ))
        print("Data rows formatted.")
    
    # ── 6. Borders ─────────────────────────────────────────────
    solid = Border(style='SOLID', width=1, color=Color(0.7, 0.7, 0.75))
    solid_dark = Border(style='SOLID', width=2, color=Color(0.5, 0.5, 0.6))
    
    # All cells border
    format_cell_range(ws, f'A1:O{num_rows}', CellFormat(
        borders=Borders(bottom=solid, right=solid, top=solid, left=solid)
    ))
    # Thick borders between tier groups
    for col in ['C', 'F', 'I', 'L']:
        format_cell_range(ws, f'{col}1:{col}{num_rows}', CellFormat(
            borders=Borders(left=solid_dark)
        ))
    print("Borders applied.")
    
    # ── 7. Conditional formatting for YES/NO ───────────────────
    # YES = green, NO = red for achieved columns
    yes_rule = ConditionalFormatRule(
        ranges=[GridRange.from_a1_range(f'D2:D{num_rows}', ws),
                GridRange.from_a1_range(f'G2:G{num_rows}', ws),
                GridRange.from_a1_range(f'J2:J{num_rows}', ws),
                GridRange.from_a1_range(f'M2:M{num_rows}', ws)],
        booleanRule=BooleanRule(
            condition=BooleanCondition('TEXT_EQ', ['YES']),
            format=CellFormat(
                backgroundColor=Color(0.73, 0.93, 0.81),
                textFormat=TextFormat(bold=True, foregroundColor=Color(0.05, 0.4, 0.18))
            )
        )
    )
    no_rule = ConditionalFormatRule(
        ranges=[GridRange.from_a1_range(f'D2:D{num_rows}', ws),
                GridRange.from_a1_range(f'G2:G{num_rows}', ws),
                GridRange.from_a1_range(f'J2:J{num_rows}', ws),
                GridRange.from_a1_range(f'M2:M{num_rows}', ws)],
        booleanRule=BooleanRule(
            condition=BooleanCondition('TEXT_EQ', ['NO']),
            format=CellFormat(
                backgroundColor=Color(0.98, 0.80, 0.80),
                textFormat=TextFormat(bold=True, foregroundColor=Color(0.6, 0.06, 0.06))
            )
        )
    )
    rules = get_conditional_format_rules(ws)
    rules.clear()
    rules.append(yes_rule)
    rules.append(no_rule)
    rules.save()
    print("Conditional formatting (YES=green, NO=red) applied.")
    
    print("\n✅ Google Sheet formatted successfully!")

if __name__ == '__main__':
    format_sheet()
