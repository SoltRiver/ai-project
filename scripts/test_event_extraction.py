"""イベント抽出ロジック検証スクリプト"""
import sys
sys.path.insert(0, ".")

from services.event_extractor import EventExtractor

e = EventExtractor()

# テストドキュメント（EDINETのdocuments.json形式を模擬）
test_docs = [
    {
        "docID": "TEST001",
        "secCode": "7203 ",
        "filerName": "トヨタ自動車株式会社",
        "docDescription": "業績予想の修正に関するお知らせ（上方修正）",
        "submitDateTime": "2024-06-15 09:00",
    },
    {
        "docID": "TEST002",
        "secCode": "6758 ",
        "filerName": "ソニーグループ株式会社",
        "docDescription": "自己株式取得に係る事項の決定に関するお知らせ",
        "submitDateTime": "2024-06-15 10:00",
    },
    {
        "docID": "TEST003",
        "secCode": "9984 ",
        "filerName": "ソフトバンクグループ株式会社",
        "docDescription": "公開買付けの中止に関するお知らせ",
        "submitDateTime": "2024-06-15 11:00",
    },
    {
        "docID": "TEST004",
        "secCode": "8306 ",
        "filerName": "三菱UFJフィナンシャル・グループ",
        "docDescription": "配当金の増額に関するお知らせ",
        "submitDateTime": "2024-06-15 12:00",
    },
    {
        "docID": "TEST005",
        "secCode": "8035 ",
        "filerName": "東京エレクトロン株式会社",
        "docDescription": "四半期報告書",
        "submitDateTime": "2024-06-15 13:00",
    },
]

print("=" * 90)
print(f"{'sec_code':^8} | {'event_type':^22} | {'impact':^10} | {'strength':^8} | {'method':^7} | title")
print("-" * 90)

total_events = 0
for doc in test_docs:
    events = e.extract_events(doc)
    if events:
        for r in events:
            print(f"  {r['sec_code']:^6} | {r['event_type']:^22} | {r['impact_type']:^10} | {r['impact_strength']:^8} | {r['extraction_method']:^7} | {r['title'][:40]}")
            total_events += 1
    else:
        print(f"  {doc['secCode'].strip():^6} | {'(抽出なし)':^22} | {'-':^10} | {'-':^8} | {'-':^7} | {doc['docDescription'][:40]}")

print("-" * 90)
print(f"合計: {len(test_docs)} 文書 → {total_events} イベント抽出")
print()

# 否定語テスト確認
print("■ 否定語テスト:")
print(f"  TEST003 (公開買付けの中止): impact_type should be NEGATIVE (TOB + 中止 → 反転)")
for doc in test_docs:
    if doc["docID"] == "TEST003":
        r = e.extract_events(doc)
        if r:
            print(f"  → 結果: impact_type={r[0]['impact_type']}, method={r[0]['extraction_method']}")
            assert r[0]["impact_type"] == "NEGATIVE", "TOB中止はNEGATIVEであるべき"
            assert r[0]["extraction_method"] == "CONTEXT", "否定語検出ではCONTEXTメソッド"
            print("  ✅ 正しい!")

print()
print("■ 非イベント文書テスト:")
print(f"  TEST005 (四半期報告書): イベント抽出なしであるべき")
for doc in test_docs:
    if doc["docID"] == "TEST005":
        r = e.extract_events(doc)
        assert len(r) == 0, "四半期報告書はイベントではない"
        print("  ✅ 正しい! (抽出0件)")

print()
print("全テスト完了 ✅")
