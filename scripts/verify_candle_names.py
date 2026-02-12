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
    
    # --- Marubozu Tests ---
    # Marubozu Bull (No shadows)
    # Range 10, Body 10. O=100, C=110, H=110, L=100
    test_pattern("Marubozu Bull", 100, 110, 100, 110, "丸坊主")

    # Closing Marubozu Bull (No Upper)
    # Range 11, Body 10. O=100, C=110, H=110, L=99
    test_pattern("Closing Marubozu Bull", 100, 110, 99, 110, "大引け坊主")

    # Opening Marubozu Bull (No Lower)
    # Range 11, Body 10. O=100, C=110, H=111, L=100
    test_pattern("Opening Marubozu Bull", 100, 111, 100, 110, "寄付き坊主")

    # Marubozu Bear (No shadows)
    # Range 10, Body 10. O=110, C=100, H=110, L=100
    test_pattern("Marubozu Bear", 110, 110, 100, 100, "丸坊主")

    # Closing Marubozu Bear (No Lower)
    # Range 11, Body 10. O=109, C=100, H=110, L=100
    test_pattern("Closing Marubozu Bear", 109, 110, 100, 100, "大引け坊主")

    # Opening Marubozu Bear (No Upper)
    # Range 11, Body 10. O=110, C=100, H=110, L=99
    test_pattern("Opening Marubozu Bear", 110, 110, 99, 100, "寄付き坊主")


    # --- Karakasa / Tonkachi Tests ---
    # Karakasa Bull (Long Lower)
    # Range 6, Body 1. O=105, C=106, H=106 (Up=0), L=100 (Lo=5)
    test_pattern("Karakasa Bull", 105, 106, 100, 106, "カラカサ")

    # Tonkachi Bull (Long Upper)
    # Range 6, Body 1. O=100, C=101, H=106 (Up=5), L=100 (Lo=0)
    test_pattern("Tonkachi Bull", 100, 106, 100, 101, "トンカチ")

    # Karakasa Bear (Long Lower)
    # Range 6, Body 1. O=106, C=105, H=106 (Up=0), L=100 (Lo=5)
    test_pattern("Karakasa Bear", 106, 106, 100, 105, "カラカサ")

    # Tonkachi Bear (Long Upper)
    # Range 6, Body 1. O=101, C=100, H=106 (Up=5), L=100 (Lo=0)
    test_pattern("Tonkachi Bear", 101, 106, 100, 100, "トンカチ")

    # One Price (Range 0)
    test_pattern("One Price", 100, 100, 100, 100, "寄引同時線")
