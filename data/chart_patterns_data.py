"""
チャートパターンデータモジュール
株価チャートパターンの情報を定義する
"""

CHART_PATTERNS = {
    "リバーサルパターン": {
        "トリプルボトム": {
            "japanese": "トリプルボトム",
            "english": "Triple Bottom",
            "overview": "3つのほぼ同じ水準の安値が形成される底値圏の反転パターン。強い買いシグナル。",
            "formation_conditions": "1. 3つの明確な安値がほぼ同じ水準で形成される\n2. 各安値の間に2つの高値がある\n3. 3つ目の安値の後に上昇トレンドが始まる\n4. 出来高は各安値で減少し、ブレイクアウト時に増加する",
            "typical_movement": "3つ目の安値形成後、2番目の高値を上抜けると上昇トレンドが始まる。目標価格は、高値と安値の差をブレイクアウトポイントに加算した水準。",
            "notes": "パターン完成には時間がかかることが多い。ブレイクアウトの確認には出来高の増加が重要。"
        },
        "トリプルトップ": {
            "japanese": "トリプルトップ",
            "english": "Triple Top",
            "overview": "3つのほぼ同じ水準の高値が形成される天井圏の反転パターン。強い売りシグナル。",
            "formation_conditions": "1. 3つの明確な高値がほぼ同じ水準で形成される\n2. 各高値の間に2つの安値がある\n3. 3つ目の高値の後に下降トレンドが始まる\n4. 出来高は各高値で減少し、ブレイクダウン時に増加する",
            "typical_movement": "3つ目の高値形成後、2番目の安値を下抜けると下降トレンドが始まる。目標価格は、高値と安値の差をブレイクダウンポイントから減算した水準。",
            "notes": "トリプルボトムと同様に、パターン完成には時間がかかる。ブレイクダウンの確認には出来高の増加が重要。"
        },
        "ダブルトップ": {
            "japanese": "ダブルトップ",
            "english": "Double Top",
            "overview": "2つのほぼ同じ水準の高値が形成される天井圏の反転パターン。",
            "formation_conditions": "1. 2つの明確な高値がほぼ同じ水準で形成される\n2. 2つの高値の間に1つの安値（ネックライン）がある\n3. ネックラインを下抜けると下降トレンドが始まる",
            "typical_movement": "ネックラインを下抜けると下降トレンドが始まる。目標価格は、高値とネックラインの差をブレイクダウンポイントから減算した水準。",
            "notes": "M字型の形状。2つ目の高値で出来高が減少することが多い。"
        },
        "ダブルボトム": {
            "japanese": "ダブルボトム",
            "english": "Double Bottom",
            "overview": "2つのほぼ同じ水準の安値が形成される底値圏の反転パターン。",
            "formation_conditions": "1. 2つの明確な安値がほぼ同じ水準で形成される\n2. 2つの安値の間に1つの高値（ネックライン）がある\n3. ネックラインを上抜けると上昇トレンドが始まる",
            "typical_movement": "ネックラインを上抜けると上昇トレンドが始まる。目標価格は、ネックラインと安値の差をブレイクアウトポイントに加算した水準。",
            "notes": "W字型の形状。2つ目の安値で出来高が減少することが多い。"
        },
        "逆三尊": {
            "japanese": "逆三尊",
            "english": "Inverse Head and Shoulders",
            "overview": "3つの安値で中央が最も低い底値圏の反転パターン。強い買いシグナル。",
            "formation_conditions": "1. 左肩、頭、右肩の3つの安値が形成される\n2. 頭が最も低く、左右の肩はほぼ同じ水準\n3. ネックライン（左右の肩を結ぶ線）を上抜けると上昇トレンドが始まる",
            "typical_movement": "ネックラインを上抜けると上昇トレンドが始まる。目標価格は、頭とネックラインの差をブレイクアウトポイントに加算した水準。",
            "notes": "出来高は頭の形成時に増加し、右肩の形成時に減少、ブレイクアウト時に増加する。"
        },
        "三尊天井": {
            "japanese": "三尊天井",
            "english": "Head and Shoulders",
            "overview": "3つの高値で中央が最も高い天井圏の反転パターン。強い売りシグナル。",
            "formation_conditions": "1. 左肩、頭、右肩の3つの高値が形成される\n2. 頭が最も高く、左右の肩はほぼ同じ水準\n3. ネックライン（左右の肩を結ぶ線）を下抜けると下降トレンドが始まる",
            "typical_movement": "ネックラインを下抜けると下降トレンドが始まる。目標価格は、頭とネックラインの差をブレイクダウンポイントから減算した水準。",
            "notes": "出来高は頭の形成時に増加し、右肩の形成時に減少、ブレイクダウン時に増加する。"
        }
    },
    "継続パターン": {
        "上昇レンジ": {
            "japanese": "上昇レンジ",
            "english": "Ascending Range",
            "overview": "上昇トレンド中の一時的な調整局面。上昇トレンドの継続を示す。",
            "formation_conditions": "1. 上昇トレンド中に形成される\n2. 上限と下限の2本の水平線または上昇線で囲まれる\n3. 上限を上抜けると上昇トレンドが継続する",
            "typical_movement": "レンジ内で上下動を繰り返した後、上限を上抜けると上昇トレンドが継続する。",
            "notes": "レンジ内での取引はリスクが高い。ブレイクアウトを待つことが推奨される。"
        },
        "下降レンジ": {
            "japanese": "下降レンジ",
            "english": "Descending Range",
            "overview": "下降トレンド中の一時的な調整局面。下降トレンドの継続を示す。",
            "formation_conditions": "1. 下降トレンド中に形成される\n2. 上限と下限の2本の水平線または下降線で囲まれる\n3. 下限を下抜けると下降トレンドが継続する",
            "typical_movement": "レンジ内で上下動を繰り返した後、下限を下抜けると下降トレンドが継続する。",
            "notes": "レンジ内での取引はリスクが高い。ブレイクダウンを待つことが推奨される。"
        },
        "上昇三角持ち合い": {
            "japanese": "上昇三角持ち合い",
            "english": "Ascending Triangle",
            "overview": "上限が水平で下限が上昇する三角形の継続パターン。上昇トレンドの継続を示す。",
            "formation_conditions": "1. 上限が水平線、下限が上昇線で形成される\n2. 上限を上抜けると上昇トレンドが継続する\n3. 出来高は減少傾向だが、ブレイクアウト時に増加する",
            "typical_movement": "三角形内で上下動の幅が狭くなり、上限を上抜けると上昇トレンドが継続する。",
            "notes": "強気の継続パターン。ブレイクアウトの確認には出来高の増加が重要。"
        },
        "下降三角持ち合い": {
            "japanese": "下降三角持ち合い",
            "english": "Descending Triangle",
            "overview": "下限が水平で上限が下降する三角形の継続パターン。下降トレンドの継続を示す。",
            "formation_conditions": "1. 下限が水平線、上限が下降線で形成される\n2. 下限を下抜けると下降トレンドが継続する\n3. 出来高は減少傾向だが、ブレイクダウン時に増加する",
            "typical_movement": "三角形内で上下動の幅が狭くなり、下限を下抜けると下降トレンドが継続する。",
            "notes": "弱気の継続パターン。ブレイクダウンの確認には出来高の増加が重要。"
        },
        "上昇フラッグ": {
            "japanese": "上昇フラッグ",
            "english": "Bullish Flag",
            "overview": "上昇トレンド中の短期的な調整局面。上昇トレンドの継続を示す。",
            "formation_conditions": "1. 強い上昇トレンドの後に形成される\n2. 短期的な下降または横ばいの調整\n3. 上限を上抜けると上昇トレンドが継続する",
            "typical_movement": "調整後、上限を上抜けると上昇トレンドが継続する。目標価格は、旗竿（最初の上昇）の高さをブレイクアウトポイントに加算した水準。",
            "notes": "短期的なパターン（数日から数週間）。出来高は調整中に減少し、ブレイクアウト時に増加する。"
        },
        "下降フラッグ": {
            "japanese": "下降フラッグ",
            "english": "Bearish Flag",
            "overview": "下降トレンド中の短期的な調整局面。下降トレンドの継続を示す。",
            "formation_conditions": "1. 強い下降トレンドの後に形成される\n2. 短期的な上昇または横ばいの調整\n3. 下限を下抜けると下降トレンドが継続する",
            "typical_movement": "調整後、下限を下抜けると下降トレンドが継続する。目標価格は、旗竿（最初の下降）の高さをブレイクダウンポイントから減算した水準。",
            "notes": "短期的なパターン（数日から数週間）。出来高は調整中に減少し、ブレイクダウン時に増加する。"
        },
        "上昇ペナント": {
            "japanese": "上昇ペナント",
            "english": "Bullish Pennant",
            "overview": "上昇トレンド中の三角形の継続パターン。上昇トレンドの継続を示す。",
            "formation_conditions": "1. 強い上昇トレンドの後に形成される\n2. 上限と下限が収束する三角形\n3. 上限を上抜けると上昇トレンドが継続する",
            "typical_movement": "三角形内で上下動の幅が狭くなり、上限を上抜けると上昇トレンドが継続する。",
            "notes": "フラッグと似ているが、三角形の形状。出来高は減少傾向だが、ブレイクアウト時に増加する。"
        },
        "下降ペナント": {
            "japanese": "下降ペナント",
            "english": "Bearish Pennant",
            "overview": "下降トレンド中の三角形の継続パターン。下降トレンドの継続を示す。",
            "formation_conditions": "1. 強い下降トレンドの後に形成される\n2. 上限と下限が収束する三角形\n3. 下限を下抜けると下降トレンドが継続する",
            "typical_movement": "三角形内で上下動の幅が狭くなり、下限を下抜けると下降トレンドが継続する。",
            "notes": "フラッグと似ているが、三角形の形状。出来高は減少傾向だが、ブレイクダウン時に増加する。"
        },
        "上昇ウェッジ": {
            "japanese": "上昇ウェッジ",
            "english": "Rising Wedge",
            "overview": "上限と下限が収束する上昇パターン。通常は弱気のシグナル。",
            "formation_conditions": "1. 上限と下限が上昇しながら収束する\n2. 上昇トレンド中に形成される場合は弱気のシグナル\n3. 下降トレンド中に形成される場合は一時的な反発",
            "typical_movement": "収束後、下限を下抜けることが多い。上昇トレンド中に形成された場合は下降転換のシグナル。",
            "notes": "見た目は強気だが、実際は弱気のシグナルとなることが多い。出来高は減少傾向。"
        },
        "下降ウェッジ": {
            "japanese": "下降ウェッジ",
            "english": "Falling Wedge",
            "overview": "上限と下限が下降しながら収束するパターン。通常は強気のシグナル。",
            "formation_conditions": "1. 上限と下限が下降しながら収束する\n2. 下降トレンド中に形成される場合は強気のシグナル\n3. 上昇トレンド中に形成される場合は一時的な調整",
            "typical_movement": "収束後、上限を上抜けることが多い。下降トレンド中に形成された場合は上昇転換のシグナル。",
            "notes": "見た目は弱気だが、実際は強気のシグナルとなることが多い。出来高は減少傾向だが、ブレイクアウト時に増加する。"
        }
    },
    "特殊パターン": {
        "ソーサートップ": {
            "japanese": "ソーサートップ",
            "english": "Saucer Top",
            "overview": "緩やかな円弧を描く天井圏の反転パターン。",
            "formation_conditions": "1. 緩やかな上昇トレンドの後に形成される\n2. 円弧状の天井を形成\n3. 下降トレンドに転換する",
            "typical_movement": "緩やかに天井を形成した後、下降トレンドが始まる。",
            "notes": "形成に時間がかかるパターン。出来高は天井形成中に減少する。"
        },
        "ソーサーボトム": {
            "japanese": "ソーサーボトム",
            "english": "Saucer Bottom",
            "overview": "緩やかな円弧を描く底値圏の反転パターン。",
            "formation_conditions": "1. 緩やかな下降トレンドの後に形成される\n2. 円弧状の底を形成\n3. 上昇トレンドに転換する",
            "typical_movement": "緩やかに底を形成した後、上昇トレンドが始まる。",
            "notes": "形成に時間がかかるパターン。出来高は底形成中に減少し、上昇開始時に増加する。"
        }
    }
}


def get_all_pattern_categories() -> list:
    """
    すべてのパターンカテゴリ名を取得
    
    Returns:
        カテゴリ名のリスト
    """
    return list(CHART_PATTERNS.keys())


def get_patterns_by_category(category: str) -> dict:
    """
    カテゴリ名からパターンデータを取得
    
    Args:
        category: カテゴリ名
    
    Returns:
        カテゴリに属するパターンの辞書
    """
    return CHART_PATTERNS.get(category, {})


def get_pattern_info(category: str, pattern_name: str) -> dict:
    """
    特定のパターンの詳細情報を取得
    
    Args:
        category: カテゴリ名
        pattern_name: パターン名
    
    Returns:
        パターンの詳細情報の辞書
    """
    category_patterns = CHART_PATTERNS.get(category, {})
    return category_patterns.get(pattern_name, {})


def search_patterns(keyword: str) -> dict:
    """
    キーワードでパターンを検索
    
    Args:
        keyword: 検索キーワード
    
    Returns:
        検索結果の辞書（カテゴリ名をキー、該当パターンの辞書を値とする）
    """
    results = {}
    keyword_lower = keyword.lower()
    
    for category, patterns in CHART_PATTERNS.items():
        matched_patterns = {}
        for pattern_name, pattern_data in patterns.items():
            # 日本語名、英語名、概要で検索
            search_text = (
                pattern_data.get("japanese", "") +
                pattern_data.get("english", "") +
                pattern_data.get("overview", "")
            ).lower()
            
            if keyword_lower in search_text:
                matched_patterns[pattern_name] = pattern_data
        
        if matched_patterns:
            results[category] = matched_patterns
    
    return results

