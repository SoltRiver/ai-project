import sys
import os

sys.path.append(os.getcwd())
from services import stock_service


def verify_90():
    print("Testing Search for '90'...")
    query = "90"
    results = stock_service.search_stocks(query)

    codes = [r["code"] for r in results]
    print(f"Results: {codes}")

    expected = ["9001", "9003", "9005"]
    missing = [e for e in expected if e not in codes]

    if not missing:
        print("PASS: Found expected 90xx codes.")
    else:
        print(f"FAIL: Missing expected codes {missing}")

    if codes == sorted(codes):
        print("PASS: Results are sorted.")
    else:
        print("FAIL: Unsorted.")


if __name__ == "__main__":
    verify_90()
