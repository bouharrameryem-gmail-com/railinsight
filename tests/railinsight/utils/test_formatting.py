"""Tests for French number and date formatters."""

import pandas as pd

from railinsight.utils.formatting import fmt_month, fmt_number, fmt_pct


class TestFmtPct:
    def test_typical_value(self):
        result = fmt_pct(0.123)
        assert "12,3" in result
        assert "%" in result

    def test_zero(self):
        result = fmt_pct(0.0)
        assert "0,0" in result
        assert "%" in result

    def test_one(self):
        result = fmt_pct(1.0)
        assert "100,0" in result
        assert "%" in result

    def test_decimals_zero(self):
        result = fmt_pct(0.5, decimals=0)
        assert "50" in result

    def test_decimals_two(self):
        result = fmt_pct(0.1234, decimals=2)
        assert "12,34" in result


class TestFmtNumber:
    def test_integer(self):
        result = fmt_number(12345)
        assert "12" in result
        assert "345" in result

    def test_small(self):
        assert fmt_number(42) == "42"

    def test_with_decimals(self):
        result = fmt_number(1234.5, decimals=1)
        assert "1" in result
        assert "234" in result
        assert ",5" in result


class TestFmtMonth:
    def test_january(self):
        assert fmt_month(pd.Period("2024-01", freq="M")) == "janvier 2024"

    def test_december(self):
        assert fmt_month(pd.Period("2023-12", freq="M")) == "décembre 2023"

    def test_all_months_non_empty(self):
        for month in range(1, 13):
            p = pd.Period(f"2024-{month:02d}", freq="M")
            result = fmt_month(p)
            assert result != ""
            assert "2024" in result
