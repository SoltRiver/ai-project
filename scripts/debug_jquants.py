from services.jquants_client import client
import os


def debug_jquants():
    print(f"Token present: {bool(os.environ.get('JQUANTS_REFRESH_TOKEN'))}")

    # Force clear cache
    client.clear_cache()

    print("Attempting to fetch listed issues...")
    issues = client.get_listed_issues()

    if not issues:
        print("FAIL: Returned empty list. Check logs for error.")
    else:
        print(f"SUCCESS: Fetched {len(issues)} issues.")
        # Check for GENDA
        genda = next((i for i in issues if "9166" in str(i.get("Code"))), None)
        if genda:
            print(f"Found GENDA: {genda}")
        else:
            print("WARN: Fetched list but GENDA (9166) not found.")


if __name__ == "__main__":
    debug_jquants()
