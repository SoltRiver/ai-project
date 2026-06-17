import sys
import os
from dotenv import load_dotenv

# Load env before importing services (though services might load it too)
load_dotenv()

sys.path.append(os.getcwd())
try:
    from services.jquants_client import client
except ImportError:
    # Handle the refactored path if needed, but sys.path should fix it
    pass


def verify_v2():
    print("--- Verifying J-Quants V2 Migration ---")

    api_key = os.environ.get("JQUANTS_API_KEY")
    refresh_token = os.environ.get("JQUANTS_REFRESH_TOKEN")

    print(f"JQUANTS_API_KEY present: {bool(api_key)}")
    print(f"JQUANTS_REFRESH_TOKEN present: {bool(refresh_token)}")

    if not api_key:
        print(
            "WARNING: JQUANTS_API_KEY is missing. Migration verification will likely fail unless Refresh Token works as API Key (unlikely)."
        )

    print("Fetching listed issues (V2)...")
    try:
        issues = client.get_listed_issues()
        if issues:
            print(f"SUCCESS: Fetched {len(issues)} issues.")
            first = issues[0]
            print(f"First 3 issues keys: {list(first.keys())}")
            print(f"Sample: {first}")

            # Check compatibility with stock_service
            if "Code" in first and ("CompanyName" in first or "Name" in first):
                print("COMPATIBILITY: Keys look compatible.")
            else:
                print(
                    "COMPATIBILITY WARN: Keys might have changed. StockService logic needs update."
                )
        else:
            print("FAILURE: Fetch returned empty list.")
    except Exception as e:
        print(f"EXCEPTION: {e}")


if __name__ == "__main__":
    verify_v2()
