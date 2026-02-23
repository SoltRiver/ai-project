"""
パフォーマンス計測スクリプト。
主要エンドポイントのレスポンスタイムを計測し、結果を表示する。
"""

import requests
import time
import statistics

BASE = "http://127.0.0.1:8000"

# 計測対象エンドポイント
ENDPOINTS = [
    # --- HTML ページ ---
    ("GET", "/",                              "ホーム（銘柄一覧）"),
    ("GET", "/glossary",                      "用語集"),
    ("GET", "/indices",                       "主要指標"),
    ("GET", "/candle-patterns",               "ローソク足パターン"),
    ("GET", "/calendar",                      "カレンダー"),
    # --- JSON API ---
    ("GET", "/api/stocks/search?q=トヨタ",     "銘柄検索API"),
    ("GET", "/edinet/health",                 "EDINET ヘルス"),
    # --- HTMX パーシャル ---
    ("GET", "/partials/edinet/diff_summary?doc_id=test", "EDINET差分パーシャル"),
]

RUNS = 3  # 各エンドポイントの計測回数


def measure(method: str, path: str, runs: int = RUNS):
    """指定回数リクエストを送り、レスポンスタイムを返す"""
    url = f"{BASE}{path}"
    times = []
    status = None
    for _ in range(runs):
        start = time.perf_counter()
        try:
            r = requests.request(method, url, timeout=30)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            status = r.status_code
            times.append(elapsed)
        except Exception as e:
            times.append(-1)
            status = f"ERR: {e}"
    return times, status


def main():
    print("=" * 72)
    print(f"  パフォーマンス計測  ({RUNS} 回平均)")
    print("=" * 72)
    print(f"{'エンドポイント':<30} {'Status':>6} {'平均(ms)':>10} {'最小':>8} {'最大':>8}")
    print("-" * 72)

    all_ok = True
    for method, path, label in ENDPOINTS:
        times, status = measure(method, path)
        valid = [t for t in times if t >= 0]
        if valid:
            avg = statistics.mean(valid)
            mn = min(valid)
            mx = max(valid)
            # 3秒超は警告
            flag = " ⚠️" if avg > 3000 else ""
            if avg > 3000:
                all_ok = False
            print(f"{label:<30} {status:>6} {avg:>9.0f}ms {mn:>7.0f} {mx:>7.0f}{flag}")
        else:
            print(f"{label:<30} {str(status):>6} {'FAIL':>10}")
            all_ok = False

    print("-" * 72)
    if all_ok:
        print("✅ 全エンドポイント 3秒以内")
    else:
        print("⚠️ 一部エンドポイントが 3秒超 または失敗")
    print("=" * 72)


if __name__ == "__main__":
    main()
