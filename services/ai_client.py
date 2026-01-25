"""
AI連携モジュール
OpenAI GPT-4系を使用して株価分析コメントやニュース解説を生成する
"""

import os
from typing import Optional, Dict, Any, List

from openai import OpenAI


def get_ai_client() -> Optional[OpenAI]:
    """環境変数からAPIキーを読み込み、OpenAIクライアントを返す"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _format_number(value: Any, digits: int = 2, suffix: str = "") -> str:
    """数値を安全にフォーマットする"""
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}{suffix}"
    return "N/A"


def generate_stock_analysis(
    symbol: str,
    stock_info: Dict[str, Any],
    technical_data: Dict[str, Any],
    fundamental_data: Dict[str, Any],
    model: str = "gpt-4o",
) -> Optional[Dict[str, str]]:
    """
    株価コメントを生成する
    """
    client = get_ai_client()
    if client is None:
        return None

    try:
        prompt = build_analysis_prompt(symbol, stock_info, technical_data, fundamental_data)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは株式市場の分析専門家です。客観性とバランスを重視し、初心者にも分かりやすく説明してください。過度な投資助言は避けてください。",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        content = response.choices[0].message.content
        return parse_ai_response(content)
    except Exception as e:
        print(f"AI分析生成エラー: {e}")
        return None


def build_analysis_prompt(
    symbol: str,
    stock_info: Dict[str, Any],
    technical_data: Dict[str, Any],
    fundamental_data: Dict[str, Any],
) -> str:
    """株式分析用プロンプトを組み立てる"""
    prompt = f"""以下の情報を基に、銘柄コード {symbol} の株式分析を行ってください。
【株価情報】
- 現在価格: {stock_info.get('current_price', 'N/A')}
- 前日比: {stock_info.get('change', 'N/A')} ({_format_number(stock_info.get('change_percent'), 2, '%')})
- 出来高: {stock_info.get('volume', 'N/A')}
- 銘柄名: {stock_info.get('name', 'N/A')}
- セクター: {stock_info.get('sector', 'N/A')}
- 業種: {stock_info.get('industry', 'N/A')}

【テクニカル分析】
{format_technical_data(technical_data)}

【ファンダメンタル分析】
- PER: {fundamental_data.get('PER', 'N/A')}
- PBR: {fundamental_data.get('PBR', 'N/A')}
- 配当利回り: {fundamental_data.get('配当利回り', 'N/A')}
- 自己資本比率: {fundamental_data.get('自己資本比率', 'N/A')}
- ROE: {fundamental_data.get('ROE', 'N/A')}
- ROA: {fundamental_data.get('ROA', 'N/A')}

以下の3つの観点から簡潔に説明してください（各3〜5行程度）。
1. プラス要因: この銘柄の強みやポジティブ要素
2. マイナス要因: この銘柄の弱みやリスク要素
3. 長期投資視点: 長期的な投資判断の参考となる情報
"""
    return prompt


def format_technical_data(technical_data: Dict[str, Any]) -> str:
    """テクニカルデータを文字列にフォーマット"""
    if not technical_data:
        return "データなし"

    def fmt(value: Any) -> str:
        return _format_number(value)

    lines: List[str] = []
    if "sma_short" in technical_data:
        lines.append(f"- 短期移動平均: {fmt(technical_data.get('sma_short'))}")
    if "sma_medium" in technical_data:
        lines.append(f"- 中期移動平均: {fmt(technical_data.get('sma_medium'))}")
    if "sma_long" in technical_data:
        lines.append(f"- 長期移動平均: {fmt(technical_data.get('sma_long'))}")
    if "trend_direction" in technical_data:
        lines.append(f"- トレンド方向: {technical_data.get('trend_direction')}")
    if "rsi" in technical_data:
        lines.append(f"- RSI: {fmt(technical_data.get('rsi'))}")
    if "golden_cross" in technical_data:
        lines.append(f"- ゴールデンクロス: {technical_data.get('golden_cross', False)}")
    if "dead_cross" in technical_data:
        lines.append(f"- デッドクロス: {technical_data.get('dead_cross', False)}")
    if "signals" in technical_data:
        lines.append(f"- シグナル: {technical_data.get('signals')}")

    return "\n".join(lines)


def parse_ai_response(content: str) -> Dict[str, str]:
    """AIレスポンスを簡易的にパースして構造化する"""
    result = {
        "plus_factors": "",
        "minus_factors": "",
        "long_term_view": "",
    }

    lower = content.lower()
    plus_idx = content.find("プラス要因")
    if plus_idx == -1:
        plus_idx = lower.find("plus")
    minus_idx = content.find("マイナス要因")
    if minus_idx == -1:
        minus_idx = lower.find("minus")
    long_idx = content.find("長期")
    if long_idx == -1:
        long_idx = lower.find("long")

    if plus_idx != -1:
        end = minus_idx if minus_idx != -1 else long_idx if long_idx != -1 else len(content)
        result["plus_factors"] = content[plus_idx:end].strip()

    if minus_idx != -1:
        end = long_idx if long_idx != -1 else len(content)
        result["minus_factors"] = content[minus_idx:end].strip()

    if long_idx != -1:
        result["long_term_view"] = content[long_idx:].strip()

    if not any(result.values()):
        result["long_term_view"] = content

    return result


def generate_news_insights(
    symbol: str,
    news_items: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
) -> Optional[str]:
    """ニュース一覧から初心者向け要約と価格インパクト解説を生成する"""
    client = get_ai_client()
    if client is None or not news_items:
        return None

    prompt_lines = [
        f"以下は銘柄 {symbol} に関連するニュースです。初心者向けに短く要約し、株価への影響を一言で付けてください。",
        "期待する出力: 箇条書きで『要約 - 株価への影響』形式。",
        "",
    ]
    for item in news_items:
        title = item.get("title", "")
        summary = item.get("summary", "")
        publisher = item.get("publisher", "")
        prompt_lines.append(f"- タイトル: {title} / 発行元: {publisher} / 内容: {summary}")

    prompt = "\n".join(prompt_lines)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "あなたは金融ニュースを分かりやすく要約するアナリストです。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ニュース要約生成エラー: {e}")
        return None


def generate_simple_analysis_fallback(
    symbol: str,
    stock_info: Dict[str, Any],
    technical_data: Dict[str, Any],
    fundamental_data: Dict[str, Any],
) -> Dict[str, str]:
    """
    AIが使用できない場合のフォールバック分析
    """
    plus_factors: List[str] = []
    minus_factors: List[str] = []
    long_term_view: List[str] = []

    if stock_info.get("change_percent", 0) > 0:
        plus_factors.append("前日比がプラスです。")

    if stock_info.get("change_percent", 0) < 0:
        minus_factors.append("前日比がマイナスです。")

    per = fundamental_data.get("PER")
    if per is not None:
        if per < 15:
            plus_factors.append("PERが相対的に低水準です。")
        elif per > 25:
            minus_factors.append("PERが高めです。")

    if fundamental_data.get("配当利回り") and fundamental_data["配当利回り"] > 0.02:
        plus_factors.append("配当利回りが良好です。")

    if technical_data.get("sma_short") and technical_data.get("sma_long"):
        if technical_data["sma_short"] > technical_data["sma_long"]:
            plus_factors.append("短期移動平均が長期移動平均を上回り、上昇傾向です。")
        else:
            minus_factors.append("短期移動平均が長期移動平均を下回り、弱含みです。")

    if fundamental_data.get("ROE") and fundamental_data["ROE"] > 0.1:
        long_term_view.append("ROEが良好で、収益性が高い可能性があります。")

    return {
        "plus_factors": "\n".join(plus_factors) if plus_factors else "特に目立ったプラス要因は見られません。",
        "minus_factors": "\n".join(minus_factors) if minus_factors else "特に目立ったマイナス要因は見られません。",
        "long_term_view": "\n".join(long_term_view) if long_term_view else "長期判断には、より詳細な分析が必要です。",
    }
