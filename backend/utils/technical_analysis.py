from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _clean_numeric_series(series: pd.Series) -> pd.Series:
    """Return a numeric Series with infinite values converted to NaN."""
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.replace([np.inf, -np.inf], np.nan)


def _none_if_nan(value: Any) -> Any:
    """Convert NaN-like scalar values to None for summaries."""
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def calculate_log_returns(close: pd.Series) -> pd.Series:
    """Compute log returns from close prices."""
    clean_close = _clean_numeric_series(close)
    returns = np.log(clean_close / clean_close.shift(1))
    return returns.replace([np.inf, -np.inf], np.nan)


def calculate_simple_returns(close: pd.Series) -> pd.Series:
    """Compute simple percentage returns from close prices."""
    clean_close = _clean_numeric_series(close)
    returns = clean_close.pct_change(fill_method=None)
    return returns.replace([np.inf, -np.inf], np.nan)


def calculate_rolling_volatility(
    close: pd.Series,
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """Compute rolling volatility from log returns."""
    log_returns = calculate_log_returns(close)
    safe_window = max(int(window), 1)
    volatility = log_returns.rolling(window=safe_window).std()

    if annualize:
        volatility = volatility * np.sqrt(252)

    return volatility


def calculate_drawdown(close: pd.Series) -> pd.Series:
    """Compute drawdown from the running maximum close price."""
    clean_close = _clean_numeric_series(close)
    running_max = clean_close.cummax()
    drawdown = (clean_close / running_max) - 1
    return drawdown.replace([np.inf, -np.inf], np.nan)


def normalize_price(close: pd.Series, base: float = 100.0) -> pd.Series:
    """Normalize the first valid close price to the provided base."""
    clean_close = _clean_numeric_series(close)
    first_valid_index = clean_close.first_valid_index()

    if first_valid_index is None:
        return pd.Series(np.nan, index=close.index, dtype="float64")

    first_valid_value = clean_close.loc[first_valid_index]
    if pd.isna(first_valid_value) or first_valid_value == 0:
        return pd.Series(np.nan, index=close.index, dtype="float64")

    normalized = (clean_close / first_valid_value) * base
    return normalized.replace([np.inf, -np.inf], np.nan)


def summarize_price_series(df: pd.DataFrame) -> dict:
    """Summarize common price and volume metrics for an OHLCV DataFrame."""
    summary = {
        "latest_close": None,
        "total_return_pct": None,
        "max_drawdown_pct": None,
        "realized_volatility_pct": None,
        "average_volume": None,
        "start_date": None,
        "end_date": None,
        "num_observations": 0,
    }

    if df is None or df.empty:
        return summary

    summary["num_observations"] = int(len(df))
    summary["start_date"] = _none_if_nan(df.index.min())
    summary["end_date"] = _none_if_nan(df.index.max())

    if "Close" in df.columns:
        close = _clean_numeric_series(df["Close"])
        valid_close = close.dropna()

        if not valid_close.empty:
            latest_close = valid_close.iloc[-1]
            first_close = valid_close.iloc[0]
            summary["latest_close"] = _none_if_nan(latest_close)

            if first_close != 0:
                total_return = (latest_close / first_close - 1) * 100
                summary["total_return_pct"] = _none_if_nan(total_return)

            drawdown = calculate_drawdown(close)
            if not drawdown.dropna().empty:
                summary["max_drawdown_pct"] = _none_if_nan(drawdown.min() * 100)

            log_returns = calculate_log_returns(close).dropna()
            if not log_returns.empty:
                realized_volatility = log_returns.std() * np.sqrt(252) * 100
                summary["realized_volatility_pct"] = _none_if_nan(realized_volatility)

    if "Volume" in df.columns:
        volume = _clean_numeric_series(df["Volume"])
        if not volume.dropna().empty:
            summary["average_volume"] = _none_if_nan(volume.mean())

    return summary
