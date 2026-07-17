import sys

file_path = "C:\\Users\\sgarm\\Downloads\\ledger_web\\portal_submit_order.py"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# Add manual mobile copying after chkaddr
new_code = code.replace(
    "page.check('#ctl00_ContentPlaceHolder1_chkaddr')\n            page.wait_for_timeout(1000)",
    "page.check('#ctl00_ContentPlaceHolder1_chkaddr')\n            page.wait_for_timeout(1000)\n\n            # Manually copy Mobile to ShipMobile because Red IDs sometimes fail to auto-fill it\n            try:\n                mobile_val = page.locator('#ctl00_ContentPlaceHolder1_txtmobile').input_value()\n                if mobile_val:\n                    page.fill('#ctl00_ContentPlaceHolder1_ShipMobile', mobile_val)\n            except Exception:\n                pass"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_code)
