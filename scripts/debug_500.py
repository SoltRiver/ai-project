import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add current directory to sys.path
sys.path.append(os.getcwd())

# Mock Request
class MockRequest:
    def __init__(self, output):
        self._output = output
        
    async def form(self):
        return self._output

async def main():
    try:
        from routers.stocks import add_stock
        from services import stock_service
        
        # Test 1: Add Stock
        print("--- Testing Add Stock ---")
        request = MockRequest({"code": "7974"}) # Nintendo
        response = await add_stock(request)
        print("Add Stock Response:", response)
        
        # Test 2: Get Stock List (simulating the page load after redirect)
        print("\n--- Testing Get Stock List ---")
        stocks = stock_service.get_stock_list()
        print(f"Retrieved {len(stocks)} stocks.")
        for s in stocks:
            print(f"- {s['code']}: {s['name']}")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
