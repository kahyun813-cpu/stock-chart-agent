import math

import pandas as pd
import pytest

from backend.utils.technical_analysis import (
    calculate_drawdown,
    calculate_log_returns,
    calculate_rolling_volatility,
    calculate_simple_returns,
    normalize_price,
    summarize_price_series,
)


@pytest.fixture
def price_series() -> pd.Series:
    index = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.Series([100, 110, 105, 120, 90], index=index, name="Close")


@pytest.fixture
def price_frame(price_series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Close": price_series,
            "Volume": [1000, 1200, 1100, 1500, 1300],
        },
        index=price_series.index,
    )


def test_calculate_simple_returns(price_series: pd.Series) -> None:
    returns = calculate_simple_returns(price_series)

    assert pd.isna(returns.iloc[0])
    assert returns.iloc[1] == pytest.approx(0.10)


def test_calculate_log_returns(price_series: pd.Series) -> None:
    returns = calculate_log_returns(price_series)

    assert pd.isna(returns.iloc[0])
    assert returns.iloc[1] == pytest.approx(math.log(110 / 100))


def test_calculate_drawdown(price_series: pd.Series) -> None:
    drawdown = calculate_drawdown(price_series)

    assert drawdown.iloc[0] == pytest.approx(0)
    assert drawdown.iloc[2] == pytest.approx(105 / 110 - 1)
    assert drawdown.iloc[4] == pytest.approx(90 / 120 - 1)


def test_normalize_price(price_series: pd.Series) -> None:
    normalized = normalize_price(price_series)

    assert normalized.iloc[0] == pytest.approx(100)
    assert normalized.iloc[1] == pytest.approx(110)


def test_calculate_rolling_volatility(price_series: pd.Series) -> None:
    volatility = calculate_rolling_volatility(price_series, window=2)

    assert isinstance(volatility, pd.Series)
    assert volatility.index.equals(price_series.index)
    assert volatility.notna().any()


def test_summarize_price_series(price_frame: pd.DataFrame) -> None:
    summary = summarize_price_series(price_frame)

    assert isinstance(summary, dict)
    assert summary["latest_close"] == pytest.approx(90)
    assert summary["total_return_pct"] == pytest.approx(-10)
    assert summary["max_drawdown_pct"] == pytest.approx(-25)
    assert summary["average_volume"] == pytest.approx(1220)
    assert summary["num_observations"] == 5
    assert summary["start_date"] is not None
    assert summary["end_date"] is not None


def test_summarize_price_series_empty_dataframe() -> None:
    summary = summarize_price_series(pd.DataFrame())

    assert summary["num_observations"] == 0
    assert summary["latest_close"] is None
    assert summary["total_return_pct"] is None
    assert summary["max_drawdown_pct"] is None
    assert summary["realized_volatility_pct"] is None
    assert summary["average_volume"] is None
