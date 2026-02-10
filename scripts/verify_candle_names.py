import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.analyzer import analyze_candlestick

def test_pattern(name, o, h, l, c, expected_name):
    result = analyze_candlestick(o, h, l, c)
    print(f"Test {name}: Expected '{expected_name}', Got '{result['name']}'")
    if result['name'] == expected_name:
        print("  [PASS]")
    else:
        print("  [FAIL]")

if __name__ == "__main__":
    print("--- Verifying Candle Names ---")
    
    # Doji (Body < 10% range)
    # Range 10, Body 0
    test_pattern("Doji", 100, 105, 95, 100, "十字線")
    
    # Marubozu / Big Candle (Body > 80% range)
    # Range 10, Body 9
    test_pattern("Big Bull", 100, 110, 100, 109, "大陽線")
    
    # Upper Shadow Bull (Upper > Body*2, Lower < Body)
    # Body 2, Upper 5, Lower 0
    # O=100, C=102. H=107 (Upp=5), L=100 (Low=0)
    test_pattern("Upper Shadow Bull", 100, 107, 100, 102, "上影陽線")
    
    # Lower Shadow Bull
    # Body 2, Lower 5, Upper 0
    # O=105, C=107. H=107 (Upp=0), L=100 (Low=5)
    test_pattern("Lower Shadow Bull", 105, 107, 100, 107, "下影陽線")

    # One Price (Range 0)
    test_pattern("One Price", 100, 100, 100, 100, "寄引同時線")
