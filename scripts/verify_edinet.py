import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from services.financial_analyzer import FinancialAnalyzer


def test_analysis():
    print("Initializing FinancialAnalyzer...")
    analyzer = FinancialAnalyzer()

    ticker = "7203"  # Toyota
    print(f"Analyzing {ticker}...")

    try:
        result = analyzer.analyze_stock(ticker)

        if result.get("financials"):
            print(" Financials Found:")
            fin = result["financials"]
            print(f"  - Sales: {fin.get('sales')}")
            print(f"  - Net Profit: {fin.get('net_profit')}")
            print(f"  - Total Assets: {fin.get('total_assets')}")
            print(f"  - Equity: {fin.get('equity')}")

            print(" Indicators:")
            ind = result["indicators"]
            print(f"  - ROE: {ind.get('ROE')}")
            print(f"  - PER: {ind.get('PER')}")
            print(f"  - PBR: {ind.get('PBR')}")

            print("SUCCESS: Data extracted and calculated.")
        else:
            print("WARNING: No financials found. (Code map issue or API issue?)")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_analysis()
