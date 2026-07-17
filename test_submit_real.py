from portal_submit_order import submit_order_to_portal

print("TEST 1: 9176AF94 with approve (THYDOC PRAVAHI KWATH [38] -)")
res1 = submit_order_to_portal('9176AF94', [{'description': 'THYDOC PRAVAHI KWATH [38] -', 'qty': 1}], 'approve')
print("Result 1:", res1)

print("\nTEST 2: 62C04A with SGO (THYDOC PRAVAHI KWATH [38] -)")
res2 = submit_order_to_portal('62C04A', [{'description': 'THYDOC PRAVAHI KWATH [38] -', 'qty': 1}], 'sgo')
print("Result 2:", res2)
