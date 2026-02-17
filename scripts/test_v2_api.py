"""
J-Quants V2 API 修正後の疎通テスト
"""
import sys
sys.path.insert(0, ".")

from services.jquants_client import client

# Test 1: コード正規化
print("=== Test 1: _normalize_code ===")
print("  8306 ->", client._normalize_code("8306"))
print("  83060 ->", client._normalize_code("83060"))
print("  8306.T ->", client._normalize_code("8306.T"))

# Test 2: get_listed_info
print("\n=== Test 2: get_listed_info (code=8306) ===")
resp = client.get_listed_info(code="8306")
if resp and "data" in resp:
    data = resp["data"]
    print("  Records:", len(data))
    if data:
        item = data[0]
        print("  Code:", item.get("Code"))
        print("  CoName:", item.get("CoName"))
        iss = item.get("IssuedShares") or item.get("NumberOfIssuedShares")
        print("  IssuedShares:", iss)
        print("  AllKeys:", sorted(item.keys()))
else:
    print("  Failed or empty:", resp)

# Test 3: get_financial_summary
print("\n=== Test 3: get_financial_summary (code=8306) ===")
records = client.get_financial_summary("8306")
print("  Records:", len(records))
if records:
    latest = records[-1]
    top_keys = sorted(latest.keys())[:12]
    print("  Keys (partial):", top_keys)
    print("  DisclosedDate:", latest.get("DisclosedDate"))

# Test 4: get_dividend (403 expected on Free plan)
print("\n=== Test 4: get_dividend (code=8306) ===")
div_records = client.get_dividend("8306")
print("  Records:", len(div_records))
if div_records:
    print("  First:", div_records[0])
else:
    print("  Empty (expected for Free plan)")

# Test 5: get_daily_quotes (older date for Free plan)
print("\n=== Test 5: get_daily_quotes ===")
quotes = client.get_daily_quotes("83060", from_date="2025-10-01", to_date="2025-10-31")
if quotes:
    dq = quotes.get("daily_quotes", [])
    print("  Records:", len(dq))
    if dq:
        print("  First: Date=%s Close=%s" % (dq[0].get("Date"), dq[0].get("Close")))
else:
    print("  Failed (Free plan date restriction)")

print("\n=== All tests completed ===")
