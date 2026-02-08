
import sys
import os

sys.path.append(os.getcwd())

from services.financial_analyzer import FinancialAnalyzer

def verify_fallback(ticker="7203"):
    print(f"Analyzing {ticker}...")
    analyzer = FinancialAnalyzer()
    analysis = analyzer.analyze_stock(ticker)
    
    print(f"Source: {analysis.get('source')}")
    print(f"Fallback Reason: {analysis.get('fallback_reason')}")

    if "error" in analysis:
        print(f"ERROR: {analysis['error']}")
    
    if "financials" in analysis:
        print("Financials found (Fallback Success!):")
        fin = analysis["financials"]
        for k, v in fin.items():
            print(f"  {k}: {v}")
    else:
        print("No financials found.")

if __name__ == "__main__":
    verify_fallback()
