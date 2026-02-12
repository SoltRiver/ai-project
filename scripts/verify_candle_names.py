import sys
import os

# プロジェクトルートをパスに追加
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
    
    # --- 十字線系テスト ---
    # 十字線 (実体 < 10%, 上下ヒゲ均等)
    # Range 10, Body 0
    test_pattern("Doji", 100, 105, 95, 100, "十字線")
    
    # トンボ (実体 < 10%, 下影が長い)
    # Range 10, Body 0, Upper=1, Lower=9
    test_pattern("Tonbo (Lower shadow)", 100, 101, 91, 100, "トンボ")
    
    # トンボ (実体 < 10%, 上影が長い)
    # Range 10, Body 0, Upper=9, Lower=1
    test_pattern("Tonbo (Upper shadow)", 100, 109, 99, 100, "トンボ")
    
    # --- 丸坊主系テスト ---
    # 丸坊主 陽線（ヒゲなし）
    test_pattern("Marubozu Bull", 100, 110, 100, 110, "丸坊主")

    # 大引け坊主 陽線（上ヒゲなし）
    test_pattern("Closing Marubozu Bull", 100, 110, 99, 110, "大引け坊主")

    # 寄付き坊主 陽線（下ヒゲなし）
    test_pattern("Opening Marubozu Bull", 100, 111, 100, 110, "寄付き坊主")

    # 丸坊主 陰線（ヒゲなし）
    test_pattern("Marubozu Bear", 110, 110, 100, 100, "丸坊主")

    # 大引け坊主 陰線（下ヒゲなし）
    test_pattern("Closing Marubozu Bear", 109, 110, 100, 100, "大引け坊主")

    # 寄付き坊主 陰線（上ヒゲなし）
    test_pattern("Opening Marubozu Bear", 110, 110, 99, 100, "寄付き坊主")

    # --- カラカサ・トンカチテスト ---
    # カラカサ 陽線（下ヒゲ長い）
    test_pattern("Karakasa Bull", 105, 106, 100, 106, "カラカサ")

    # トンカチ 陽線（上ヒゲ長い）
    test_pattern("Tonkachi Bull", 100, 106, 100, 101, "トンカチ")

    # カラカサ 陰線（下ヒゲ長い）
    test_pattern("Karakasa Bear", 106, 106, 100, 105, "カラカサ")

    # トンカチ 陰線（上ヒゲ長い）
    test_pattern("Tonkachi Bear", 101, 106, 100, 100, "トンカチ")

    # --- コマテスト ---
    # コマ（実体小、上下にヒゲ長い）
    # Range 10, Body 1 (ratio=0.1), Upper=4, Lower=5
    test_pattern("Koma", 104, 109, 99, 105, "コマ")

    # 上ヒゲ陽線（上ヒゲ目立つ、下ヒゲ短い）
    # Range 11, Body 4, Upper=7, Lower=0. shadow(7) > body*1.5(6) かつ shadow(7) < body*2(8)
    test_pattern("Upper Shadow Bull", 100, 111, 100, 104, "上ヒゲ陽線")

    # 下ヒゲ陽線（下ヒゲ目立つ、上ヒゲ短い）
    # Range 11, Body 4, Upper=0, Lower=7. shadow(7) > body*1.5(6) かつ shadow(7) < body*2(8)
    test_pattern("Lower Shadow Bull", 104, 108, 97, 108, "下ヒゲ陽線")

    # --- 寄引同時線テスト ---
    test_pattern("One Price", 100, 100, 100, 100, "寄引同時線")
