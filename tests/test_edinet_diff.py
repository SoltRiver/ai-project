"""
EDINET 差分比較サービスのユニットテスト。

テスト対象:
- normalize_unit: 単位変換
- compute_fixed_six: 固定6項目の差分計算
- extract_top_changes: 変化大3件の抽出
- _compute_equity_ratio: 自己資本比率算出
"""

import pytest
from decimal import Decimal
from services.edinet_diff_service import (
    normalize_unit,
    compute_fixed_six,
    extract_top_changes,
    _compute_equity_ratio,
    FIXED_SIX_KEYS,
)

# ==============================================================
# normalize_unit テスト
# ==============================================================


class TestNormalizeUnit:
    """単位正規化のテスト"""

    def test_jpy_そのまま(self):
        """JPY 単位は変換なし"""
        val, unit = normalize_unit(1000, "JPY")
        assert val == Decimal("1000")
        assert unit == "JPY"

    def test_thousand_jpy(self):
        """千円 → JPY 変換"""
        val, unit = normalize_unit(500, "thousand_JPY")
        assert val == Decimal("500000")
        assert unit == "JPY"

    def test_million_jpy(self):
        """百万円 → JPY 変換"""
        val, unit = normalize_unit(100, "million_JPY")
        assert val == Decimal("100000000")
        assert unit == "JPY"

    def test_日本語単位_円(self):
        """日本語「円」は JPY と同等"""
        val, unit = normalize_unit(999, "円")
        assert val == Decimal("999")
        assert unit == "JPY"

    def test_日本語単位_千円(self):
        """日本語「千円」"""
        val, unit = normalize_unit(10, "千円")
        assert val == Decimal("10000")
        assert unit == "JPY"

    def test_日本語単位_百万円(self):
        """日本語「百万円」"""
        val, unit = normalize_unit(5, "百万円")
        assert val == Decimal("5000000")
        assert unit == "JPY"

    def test_不明単位は欠損(self):
        """変換不能な単位は None を返す"""
        val, unit = normalize_unit(100, "USD")
        assert val is None
        assert unit == "unknown"

    def test_none値は欠損(self):
        """値が None の場合"""
        val, unit = normalize_unit(None, "JPY")
        assert val is None
        assert unit == "unknown"

    def test_単位なしの場合JPY仮定(self):
        """単位が None の場合は JPY を仮定"""
        val, unit = normalize_unit(1234, None)
        assert val == Decimal("1234")
        assert unit == "JPY"

    def test_文字列数値も変換(self):
        """文字列で渡された数値も正しく変換"""
        val, unit = normalize_unit("500000", "JPY")
        assert val == Decimal("500000")

    def test_無効な値は欠損(self):
        """数値に変換できない値"""
        val, unit = normalize_unit("abc", "JPY")
        assert val is None


# ==============================================================
# compute_fixed_six テスト
# ==============================================================


class TestComputeFixedSix:
    """固定6項目の差分計算テスト"""

    def _make_facts(self, **kwargs):
        """テスト用の facts 辞書を作成"""
        facts = {}
        for key, value in kwargs.items():
            facts[key] = {
                "value": Decimal(str(value)) if value is not None else None,
                "unit": "JPY",
                "consolidation_scope": "consolidated",
                "source_locator": f"test:{key}",
            }
        return facts

    def test_正常な差分計算(self):
        """全項目揃っている場合の差分計算"""
        current = self._make_facts(
            revenue=100000,
            operating_profit=20000,
            net_income=10000,
            operating_cf=15000,
            total_assets=500000,
            equity=200000,
        )
        prev = self._make_facts(
            revenue=90000,
            operating_profit=18000,
            net_income=9000,
            operating_cf=14000,
            total_assets=480000,
            equity=190000,
        )
        results, notes = compute_fixed_six(current, prev)

        assert len(results) == 6  # 常に6項目
        # revenue の差分チェック
        revenue = results[0]
        assert revenue["metric_key"] == "revenue"
        assert revenue["is_missing"] is False
        assert Decimal(revenue["delta"]) == Decimal("10000")

    def test_prev無しの場合(self):
        """prev が None の場合は差分なし（今回のみ）"""
        current = self._make_facts(
            revenue=100000,
            operating_profit=20000,
            net_income=10000,
            operating_cf=15000,
            total_assets=500000,
            equity=200000,
        )
        results, notes = compute_fixed_six(current, None)

        assert len(results) == 6
        for item in results:
            assert item["prev_value"] is None or item["is_missing"] is True

    def test_欠損値がある場合(self):
        """一部指標が欠損の場合"""
        current = self._make_facts(revenue=100000, total_assets=500000)
        prev = self._make_facts(revenue=90000, total_assets=480000)
        results, notes = compute_fixed_six(current, prev)

        assert len(results) == 6
        # operating_profit は欠損
        op = next(r for r in results if r["metric_key"] == "operating_profit")
        assert op["is_missing"] is True

    def test_equity_ratio_計算(self):
        """equity_ratio が正しく算出されること"""
        current = self._make_facts(
            revenue=100000,
            operating_profit=20000,
            net_income=10000,
            operating_cf=15000,
            total_assets=500000,
            equity=200000,
        )
        results, notes = compute_fixed_six(current, None)

        er = next(r for r in results if r["metric_key"] == "equity_ratio")
        assert er["is_missing"] is False
        # 200000 / 500000 = 0.4
        assert float(Decimal(er["current_value"])) == pytest.approx(0.4, rel=1e-3)

    def test_equity_欠損時の固定notes(self):
        """equity が無い場合は固定 notes を出力"""
        current = self._make_facts(
            revenue=100000,
            operating_profit=20000,
            net_income=10000,
            operating_cf=15000,
            total_assets=500000,
        )
        results, notes = compute_fixed_six(current, None)
        assert any("自己資本が未取得のため算出不可" in n for n in notes)

    def test_prev_value_0の場合delta_pctはnull(self):
        """prev_value が 0 の場合、delta_pct は None"""
        current = self._make_facts(
            revenue=100000,
            operating_profit=20000,
            net_income=10000,
            operating_cf=15000,
            total_assets=500000,
            equity=200000,
        )
        prev = self._make_facts(
            revenue=0,
            operating_profit=18000,
            net_income=9000,
            operating_cf=14000,
            total_assets=480000,
            equity=190000,
        )
        results, notes = compute_fixed_six(current, prev)
        revenue = results[0]
        assert revenue["delta_pct"] is None  # prev = 0


# ==============================================================
# extract_top_changes テスト
# ==============================================================


class TestExtractTopChanges:
    """変化大3件抽出のテスト"""

    def _make_facts(self, **kwargs):
        """テスト用の facts 辞書"""
        facts = {}
        for key, value in kwargs.items():
            facts[key] = {
                "value": Decimal(str(value)) if value is not None else None,
                "unit": "JPY",
                "consolidation_scope": "consolidated",
                "source_locator": f"test:{key}",
            }
        return facts

    def test_total_assets_欠損で抽出不可(self):
        """total_assets が無い場合は抽出を行わない"""
        current = self._make_facts(ordinary_profit=100)
        prev = self._make_facts(ordinary_profit=50)
        results, error = extract_top_changes(current, prev, FIXED_SIX_KEYS)
        assert len(results) == 0
        assert "総資産" in error

    def test_候補0件の場合(self):
        """閾値を満たす候補が無い場合"""
        current = self._make_facts(
            total_assets=1000000,
            ordinary_profit=1000,
        )
        prev = self._make_facts(
            total_assets=1000000,
            ordinary_profit=1001,  # ほぼ変化なし
        )
        results, error = extract_top_changes(current, prev, FIXED_SIX_KEYS)
        assert error is None
        assert len(results) == 0

    def test_最大3件で切り捨て(self):
        """4件以上の候補がある場合でも最大3件"""
        current = self._make_facts(
            total_assets=1000000,
            ordinary_profit=200000,  # 大きな変化
            investing_cf=-300000,  # 大きな変化
            financing_cf=-200000,  # 大きな変化
            cash_end=500000,  # 大きな変化
            net_assets=600000,  # 大きな変化
        )
        prev = self._make_facts(
            total_assets=1000000,
            ordinary_profit=50000,
            investing_cf=-100000,
            financing_cf=-50000,
            cash_end=200000,
            net_assets=300000,
        )
        results, error = extract_top_changes(current, prev, FIXED_SIX_KEYS)
        assert error is None
        assert len(results) <= 3

    def test_固定6は候補から除外(self):
        """固定6項目のキーは変化大候補から除外"""
        current = self._make_facts(
            total_assets=1000000,
            revenue=500000,  # これは固定6
        )
        prev = self._make_facts(
            total_assets=1000000,
            revenue=100000,
        )
        results, error = extract_top_changes(current, prev, FIXED_SIX_KEYS)
        for r in results:
            assert r["metric_key"] not in FIXED_SIX_KEYS


# ==============================================================
# _compute_equity_ratio テスト
# ==============================================================


class TestComputeEquityRatio:
    """自己資本比率算出のテスト"""

    def test_正常算出(self):
        """equity / total_assets が正しく計算される"""
        facts = {
            "equity": {
                "value": Decimal("300000"),
                "consolidation_scope": "consolidated",
                "source_locator": "eq",
            },
            "total_assets": {
                "value": Decimal("1000000"),
                "consolidation_scope": "consolidated",
                "source_locator": "ta",
            },
        }
        notes = []
        _compute_equity_ratio(facts, notes, "今回")
        assert "equity_ratio" in facts
        assert float(facts["equity_ratio"]["value"]) == pytest.approx(0.3, rel=1e-3)
        assert len(notes) == 0

    def test_equity欠損(self):
        """equity が無い場合は notes に固定文"""
        facts = {
            "total_assets": {
                "value": Decimal("1000000"),
                "consolidation_scope": "consolidated",
                "source_locator": "ta",
            },
        }
        notes = []
        _compute_equity_ratio(facts, notes, "今回")
        assert "equity_ratio" not in facts
        assert any("自己資本が未取得" in n for n in notes)

    def test_total_assets_0(self):
        """total_assets が 0 の場合"""
        facts = {
            "equity": {
                "value": Decimal("300000"),
                "consolidation_scope": "consolidated",
                "source_locator": "eq",
            },
            "total_assets": {
                "value": Decimal("0"),
                "consolidation_scope": "consolidated",
                "source_locator": "ta",
            },
        }
        notes = []
        _compute_equity_ratio(facts, notes, "今回")
        assert "equity_ratio" not in facts
        assert len(notes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
