import json

def test_match(inv_name, db_name):
    norm_desc = inv_name.replace('\n', ' ').replace(' -', '').strip().upper()
    c3_val = db_name.replace('\n', ' ').replace(' -', '').strip().upper()
    return norm_desc == c3_val, norm_desc, c3_val

print(test_match("LUXE MATTE LIQUID LIPSTICK- HALEN [451]", "LUXE MATTE LIQUID LIPSTICK- HALEN\n[451] -"))
