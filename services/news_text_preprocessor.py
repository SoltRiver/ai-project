"""
ニュース本文前処理モジュール
AIに渡す前にテキストを短縮し、トークン消費を削減する。
不要な定型文（ナビ、広告、フッター等）を除去し、重要段落を優先保持する。
"""

import re
import hashlib
from typing import Optional


# ================================================================
# 除去対象パターン（正規表現）
# ================================================================

# ナビゲーション・メニュー的な文言
_NAV_PATTERNS = [
    r"(?m)^(Home|Menu|Navigation|Top|Back to top|ホーム|メニュー|トップへ戻る)[\s]*$",
    r"(?m)^(Share|Tweet|Facebook|LINE|はてブ|シェア|共有)[\s]*$",
]

# 関連記事リンク
_RELATED_PATTERNS = [
    r"(?m)^(関連記事|おすすめ記事|あわせて読みたい|Related Articles?|See Also|もっと読む).*$",
    r"(?m)^(【関連】|▼関連|■関連).*$",
]

# 広告・PR文
_AD_PATTERNS = [
    r"(?m)^(PR|広告|Sponsored|Advertisement|提供|AD|【PR】|【広告】).*$",
    r"(?m)^(この記事は広告|記事広告|タイアップ).*$",
]

# フッター定型文
_FOOTER_PATTERNS = [
    r"(?m)^(Copyright|©|All rights reserved|無断転載禁止|転載・引用禁止).*$",
    r"(?m)^(お問い合わせ|Contact|編集部|配信元|記者|取材・文|写真|撮影).*$",
    r"(?m)^(免責事項|Disclaimer|投資は自己責任|特定の金融商品).*$",
]

# 著者紹介
_AUTHOR_PATTERNS = [
    r"(?m)^(著者プロフィール|筆者紹介|About the Author|ライター|記者).*$",
    r"(?m)^(この記事を書いた人).*$",
]

# 会社概要定型文
_COMPANY_BOILERPLATE = [
    r"(?m)^(会社概要|About Us|企業情報|Company Profile).*$",
]

# 免責文
_DISCLAIMER_PATTERNS = [
    r"(?m)^(※この記事は|※本記事は|注意：|Note:).*$",
    r"(投資判断は.*自己責任|金融商品取引法|特定の銘柄.*推奨するものではありません)",
]

# 全パターンをコンパイル
_ALL_REMOVE_PATTERNS = []
for pattern_list in [
    _NAV_PATTERNS, _RELATED_PATTERNS, _AD_PATTERNS,
    _FOOTER_PATTERNS, _AUTHOR_PATTERNS, _COMPANY_BOILERPLATE,
    _DISCLAIMER_PATTERNS,
]:
    for p in pattern_list:
        _ALL_REMOVE_PATTERNS.append(re.compile(p, re.IGNORECASE))

# ================================================================
# 重要キーワード（優先保持対象）
# ================================================================
_IMPORTANT_KEYWORDS = [
    "決算", "業績", "売上", "営業利益", "純利益", "経常利益",
    "上方修正", "下方修正", "増収", "減収", "増益", "減益",
    "株価", "時価総額", "PER", "PBR", "ROE", "ROA",
    "提携", "買収", "合併", "M&A", "TOB", "MBO",
    "自社株買い", "増配", "減配", "配当",
    "受注", "新製品", "新サービス", "特許",
    "行政処分", "不正", "訴訟", "リコール",
    "上場", "IPO", "上場廃止",
    "円安", "円高", "為替", "金利", "利上げ", "利下げ",
    "GDP", "景気", "インフレ", "デフレ",
    # 英語キーワード
    "earnings", "revenue", "profit", "acquisition", "merger",
    "dividend", "buyback", "IPO", "guidance", "forecast",
]


def remove_noise_text(text: str) -> str:
    """
    不要な定型文を除去する。
    ナビ、広告、フッター、著者紹介、会社概要等を削除。
    """
    if not text:
        return ""

    result = text
    for pattern in _ALL_REMOVE_PATTERNS:
        result = pattern.sub("", result)

    return result


def remove_duplicate_paragraphs(text: str) -> str:
    """
    重複する段落を除去する。
    """
    if not text:
        return ""

    paragraphs = text.split("\n\n")
    seen = set()
    unique = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        # 正規化して比較（スペースや改行の違いを吸収）
        normalized = re.sub(r"\s+", " ", stripped).lower()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(stripped)

    return "\n\n".join(unique)


def extract_important_paragraphs(text: str, max_chars: int = 2000) -> str:
    """
    重要段落を優先して保持し、指定文字数以内に収める。
    重要キーワードを含む段落を優先度高として並べ替える。
    """
    if not text or len(text) <= max_chars:
        return text

    paragraphs = text.split("\n\n")
    if not paragraphs:
        return text[:max_chars]

    # 各段落にスコアを付与（重要キーワード含有数）
    scored = []
    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        if not stripped:
            continue
        score = sum(1 for kw in _IMPORTANT_KEYWORDS if kw in stripped)
        # 冒頭段落にはボーナスを付与（リード文は重要）
        if i < 3:
            score += 5
        scored.append((score, i, stripped))

    # スコア降順でソートし、元の順序も考慮
    scored.sort(key=lambda x: (-x[0], x[1]))

    # 文字数制限内で段落を選択
    selected = []
    total_chars = 0
    for score, idx, para in scored:
        if total_chars + len(para) > max_chars:
            # 残り文字数に入る分だけ追加
            remaining = max_chars - total_chars
            if remaining > 100:
                selected.append((idx, para[:remaining] + "…"))
                total_chars += remaining
            break
        selected.append((idx, para))
        total_chars += len(para)

    # 元の順序で結合
    selected.sort(key=lambda x: x[0])
    return "\n\n".join(para for _, para in selected)


def preprocess_news_text(
    title: str,
    raw_text: str,
    max_chars: int = 2000
) -> str:
    """
    ニュース本文をAI入力用に前処理する。
    1. 不要テキスト除去
    2. 重複段落除去
    3. 重要段落を優先保持して文字数制限
    4. タイトルを先頭に付与
    """
    # Step 1: ノイズ除去
    cleaned = remove_noise_text(raw_text)

    # Step 2: 重複段落除去
    cleaned = remove_duplicate_paragraphs(cleaned)

    # Step 3: 重要段落を優先保持
    # タイトル分の文字数を確保
    body_max = max_chars - len(title) - 20
    if body_max < 200:
        body_max = 200
    cleaned = extract_important_paragraphs(cleaned, max_chars=body_max)

    # Step 4: タイトル先頭付与
    result = f"【タイトル】{title}\n\n{cleaned}"

    return result.strip()


def compute_text_hash(text: str) -> str:
    """
    テキストのSHA256ハッシュを計算する。
    再分析判定で使用。
    """
    if not text:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
