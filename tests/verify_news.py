import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.news_service import fetch_and_analyze_market_news

def verify_news():
    print("Fetching and analyzing market news...")
    news = fetch_and_analyze_market_news()
    
    if not news:
        print("[WARN] No news found. This might be due to market hours or API limits.")
        return

    print(f"Found {len(news)} news items.")
    for item in news:
        print("-" * 50)
        print(f"Title: {item.get('title')}")
        print(f"Summary (AI): {item.get('ai_summary')}")
        impacts = item.get("impacted_stocks", [])
        if impacts:
            print("Impacts:")
            for stock in impacts:
                print(f"  - [{stock.get('impact_type')}] {stock.get('name')}: {stock.get('reason')}")
        else:
            print("No specific impacted stocks identified.")

if __name__ == "__main__":
    verify_news()
