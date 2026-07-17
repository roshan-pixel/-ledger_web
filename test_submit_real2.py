from portal_submit_order import submit_order_to_portal

import traceback

try:
    print("TEST 1: 9176AF94 with approve (THYDOC PRAVAHI KWATH [38] -)")
    res1 = submit_order_to_portal('9176AF94', [{'description': 'THYDOC PRAVAHI KWATH [38] -', 'qty': 1}], 'approve')
    print("Result 1:", res1)
except Exception as e:
    traceback.print_exc()
