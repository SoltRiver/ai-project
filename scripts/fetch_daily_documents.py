import sys
import argparse
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load env
load_dotenv()

# Add project root
sys.path.insert(0, ".")

from services.edinet_processor import EdinetProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Fetch EDINET documents for a specific date."
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date (YYYY-MM-DD). Defaults to today.",
        default=None,
    )

    args = parser.parse_args()

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.")
            return
    else:
        target_date = date.today()

    print(f"--- EDINET Daily Fetch: {target_date} ---")

    processor = EdinetProcessor()
    processor.run_daily_process(target_date)


if __name__ == "__main__":
    main()
