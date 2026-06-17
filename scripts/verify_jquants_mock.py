import sys
import os
from unittest.mock import MagicMock

# Ensure project root is in path
sys.path.append(os.getcwd())

from services import stock_service
from services import jquants_client


def verify_jquants_mock():
    print("Verifying J-Quants Search with Mock...")

    # Mock the client
    mock_issues = [
        {
            "Code": "94320",
            "CompanyName": "Nippon Telegraph and Telephone Corporation",
        },  # 5-digit code example? J-Quants uses 5 digit for some reason?
        {"Code": "9432", "CompanyName": "日本電信電話"},  # Standard
        {"Code": "9983", "CompanyName": "Fast Retailing"},
    ]

    # Patch the global client instance's method
    original_method = jquants_client.client.get_listed_issues
    jquants_client.client.get_listed_issues = MagicMock(return_value=mock_issues)

    try:
        # Test 1: Search for '9432' (Code)
        print("\n[Mock Test 1: Code 9432]")
        results = stock_service.search_stocks("9432")
        print(f"Results: {results}")
        if any(r["code"] == "9432" for r in results):
            print("PASS: Found 9432.")
        else:
            print("FAIL: Did not find 9432.")

        # Test 2: Search for 'Fast' (Name)
        print("\n[Mock Test 2: Name 'Fast']")
        results = stock_service.search_stocks("Fast")
        print(f"Results: {results}")
        if any(r["code"] == "9983" for r in results):
            print("PASS: Found Fast Retailing.")
        else:
            print("FAIL: Did not find Fast Retailing.")

    finally:
        # Restore
        jquants_client.client.get_listed_issues = original_method


if __name__ == "__main__":
    verify_jquants_mock()
