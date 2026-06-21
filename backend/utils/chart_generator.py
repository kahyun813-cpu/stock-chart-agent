import os
import re
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from plotly.subplots import make_subplots

from backend.utils.technical_analysis import (
    calculate_drawdown,
    calculate_rolling_volatility,
    calculate_simple_returns,
    normalize_price,
    summarize_price_series,
)

CHARTS_DIR = os.getenv("CHARTS_DIR", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

SUPPORTED_INDICATORS = {
    "ma",
    "rsi",
    "volume",
    "returns",
    "volatility",
    "drawdown",
    "normalized",
}

DEMO_FALLBACK_TICKERS = {
    "AAPL",
    "MSFT",
    "GOOGL",
    "TSLA",
    "NVDA",
    "005930.KS",
    "000660.KS",
}


def _safe_filename_part(value: str) -> str:
    """Convert dynamic filename parts to filesystem-safe text."""
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value)
    return safe.strip("_") or "chart"


def _serialize_summary(summary: dict) -> dict:
    """Convert date-like summary values to strings for API/UI display."""
    serialized = dict(summary)
    for key in ("start_date", "end_date"):
        value = serialized.get(key)
        if value is not None:
            serialized[key] = str(value)
    return serialized


def _demo_row_count(period: str, interval: str) -> int:
    if interval in {"1m", "5m", "15m", "30m", "60m", "1h"}:
        return 40 if period in {"1d", "5d"} else 60
    return {
        "1d": 24,
        "5d": 5,
        "1mo": 30,
        "3mo": 65,
        "6mo": 126,
        "1y": 252,
        "2y": 504,
        "5y": 1260,
        "ytd": 180,
        "max": 500,
    }.get(period, 30)


def _generate_demo_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Generate deterministic fallback OHLCV data for local demos."""
    count = _demo_row_count(period, interval)
    freq = "h" if interval in {"1m", "5m", "15m", "30m", "60m", "1h"} else "D"
    seed = sum(ord(char) for char in ticker)
    rng = np.random.default_rng(seed)
    base_price = 80 + (seed % 180)
    drift = ((seed % 9) - 4) / 1000

    returns = rng.normal(loc=drift, scale=0.018, size=count)
    close = base_price * np.cumprod(1 + returns)
    open_values = np.r_[close[0], close[:-1]]
    high = np.maximum(open_values, close) * (1 + rng.uniform(0.002, 0.018, size=count))
    low = np.minimum(open_values, close) * (1 - rng.uniform(0.002, 0.018, size=count))
    volume = rng.integers(800_000, 8_000_000, size=count)
    index = pd.date_range(end=pd.Timestamp.now().floor("h"), periods=count, freq=freq)

    df = pd.DataFrame(
        {
            "Open": open_values,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )
    df.attrs["data_source"] = "demo"
    return df


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate the relative strength index."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def validate_interval_period(interval: str, period: str) -> Optional[str]:
    """Return an error message when an interval/period combination is unsupported."""
    minute_intervals = {"1m", "5m", "15m", "30m", "60m"}
    valid_short_periods = {"1d", "5d", "7d"}

    if interval in minute_intervals and period not in valid_short_periods:
        return (
            "**Interval-Period Mismatch!**\n"
            f"`{interval}` only supports short lookback periods.\n\n"
            "**Fix options:**\n"
            "- Option 1: Change period to `1d` or `5d`\n"
            "- Option 2: Change interval to `1h`, `1d`, or `1wk`"
        )
    return None


def fetch_ticker_data(ticker: str, period: str, interval: str) -> tuple[pd.DataFrame, str]:
    """Fetch OHLCV data with yfinance, falling back to demo data for known demo tickers."""
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)

        if df is None or df.empty:
            if ticker in DEMO_FALLBACK_TICKERS:
                return _generate_demo_data(ticker, period, interval), ""
            return pd.DataFrame(), (
                f"No data was found for `{ticker}`.\n"
                "- US stocks: `AAPL`, `MSFT`, `TSLA`, `NVDA`\n"
                "- Korean market stocks: `005930.KS`, `000660.KS`\n"
                "- ETFs: `SPY`, `QQQ`, `ARKK`\n"
                "Please check the ticker symbol and period/interval combination."
            )

        df.columns = [column.capitalize() for column in df.columns]

        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = [column for column in required if column not in df.columns]
        if missing:
            return pd.DataFrame(), (
                f"`{ticker}` data is missing required columns: {missing}. "
                "Try another period or interval."
            )

        return df, ""

    except Exception as e:
        if ticker in DEMO_FALLBACK_TICKERS:
            return _generate_demo_data(ticker, period, interval), ""
        return pd.DataFrame(), f"Error while fetching `{ticker}` data: {str(e)}"


def create_chart(
    tickers: list[str],
    period: str,
    interval: str,
    chart_type: str = "candle",
    indicators: list[str] = None,
) -> dict:
    """Create a Plotly HTML chart and return chart metadata."""
    if indicators is None:
        indicators = []

    parsed_indicators = [indicator.strip().lower() for indicator in indicators if indicator]
    indicators = list(
        dict.fromkeys(
            indicator
            for indicator in parsed_indicators
            if indicator in SUPPORTED_INDICATORS
        )
    )

    stock_data = {}
    for ticker in tickers:
        df, error = fetch_ticker_data(ticker, period, interval)
        if error:
            return {"success": False, "error": error}
        stock_data[ticker] = df

    summary = {
        ticker: _serialize_summary(summarize_price_series(df))
        for ticker, df in stock_data.items()
    }
    data_source = "demo" if any(
        df.attrs.get("data_source") == "demo" for df in stock_data.values()
    ) else "yfinance"

    has_rsi = "rsi" in indicators
    has_volume = "volume" in indicators
    has_returns = "returns" in indicators
    has_volatility = "volatility" in indicators
    has_drawdown = "drawdown" in indicators
    has_normalized = "normalized" in indicators

    if has_normalized:
        chart_type = "line"

    subplot_rows = 1
    row_heights = [0.65]
    subplot_titles = ["Normalized Price (Base 100)" if has_normalized else "Price"]
    row_map = {}

    if has_rsi:
        subplot_rows += 1
        row_heights.append(0.2)
        subplot_titles.append("RSI (14)")
        row_map["rsi"] = subplot_rows
    if has_volume:
        subplot_rows += 1
        row_heights.append(0.15)
        subplot_titles.append("Volume")
        row_map["volume"] = subplot_rows
    if has_returns:
        subplot_rows += 1
        row_heights.append(0.16)
        subplot_titles.append("Returns (%)")
        row_map["returns"] = subplot_rows
    if has_volatility:
        subplot_rows += 1
        row_heights.append(0.16)
        subplot_titles.append("Rolling Volatility 20-period (%)")
        row_map["volatility"] = subplot_rows
    if has_drawdown:
        subplot_rows += 1
        row_heights.append(0.16)
        subplot_titles.append("Drawdown (%)")
        row_map["drawdown"] = subplot_rows

    fig = make_subplots(
        rows=subplot_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    line_colors = ["#00D4FF", "#FF6B6B", "#51CF66", "#FFE066", "#CC5DE8"]

    for idx, (ticker, df) in enumerate(stock_data.items()):
        color = line_colors[idx % len(line_colors)]

        if chart_type == "candle" and len(tickers) == 1 and not has_normalized:
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name=ticker,
                    increasing=dict(line=dict(color="#26A69A"), fillcolor="#26A69A"),
                    decreasing=dict(line=dict(color="#EF5350"), fillcolor="#EF5350"),
                ),
                row=1,
                col=1,
            )
        else:
            y_values = normalize_price(df["Close"]) if has_normalized else df["Close"]
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=y_values,
                    mode="lines",
                    name=ticker,
                    line=dict(color=color, width=2),
                ),
                row=1,
                col=1,
            )

        if "ma" in indicators and not has_normalized:
            ma_configs = [
                (20, "#FF6B6B", "MA20"),
                (50, "#FFE066", "MA50"),
                (200, "#51CF66", "MA200"),
            ]
            for window, ma_color, ma_name in ma_configs:
                if len(df) >= window:
                    ma_values = df["Close"].rolling(window=window).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=ma_values,
                            mode="lines",
                            name=f"{ticker} {ma_name}" if len(tickers) > 1 else ma_name,
                            line=dict(color=ma_color, width=1.2, dash="dot"),
                            opacity=0.85,
                        ),
                        row=1,
                        col=1,
                    )

        if has_rsi:
            rsi_values = calculate_rsi(df["Close"])
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=rsi_values,
                    mode="lines",
                    name=f"{ticker} RSI" if len(tickers) > 1 else "RSI",
                    line=dict(color="#A78BFA", width=1.5),
                ),
                row=row_map["rsi"],
                col=1,
            )
            fig.add_hline(
                y=70,
                line=dict(color="#EF5350", dash="dash", width=1),
                opacity=0.6,
                row=row_map["rsi"],
                col=1,
            )
            fig.add_hline(
                y=30,
                line=dict(color="#26A69A", dash="dash", width=1),
                opacity=0.6,
                row=row_map["rsi"],
                col=1,
            )
            fig.update_yaxes(range=[0, 100], row=row_map["rsi"], col=1)

        if has_volume:
            close_values = df["Close"].values
            volume_colors = [
                "#26A69A" if i == 0 or close_values[i] >= close_values[i - 1] else "#EF5350"
                for i in range(len(close_values))
            ]
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df["Volume"],
                    name=f"{ticker} Volume" if len(tickers) > 1 else "Volume",
                    marker=dict(color=volume_colors, opacity=0.8),
                ),
                row=row_map["volume"],
                col=1,
            )

        if has_returns:
            returns_pct = calculate_simple_returns(df["Close"]) * 100
            return_colors = [
                "#26A69A" if value >= 0 else "#EF5350"
                for value in returns_pct.fillna(0)
            ]
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=returns_pct,
                    name=f"{ticker} Returns" if len(tickers) > 1 else "Returns",
                    marker=dict(color=return_colors, opacity=0.8),
                ),
                row=row_map["returns"],
                col=1,
            )

        if has_volatility:
            volatility_pct = calculate_rolling_volatility(df["Close"], window=20) * 100
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=volatility_pct,
                    mode="lines",
                    name=f"{ticker} Volatility" if len(tickers) > 1 else "Volatility",
                    line=dict(color=color, width=1.5),
                ),
                row=row_map["volatility"],
                col=1,
            )

        if has_drawdown:
            drawdown_pct = calculate_drawdown(df["Close"]) * 100
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=drawdown_pct,
                    mode="lines",
                    name=f"{ticker} Drawdown" if len(tickers) > 1 else "Drawdown",
                    line=dict(color=color, width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(239,83,80,0.12)",
                ),
                row=row_map["drawdown"],
                col=1,
            )

    title_tickers = " | ".join(tickers)
    indicators_str = ", ".join(indicators).upper() if indicators else "No Indicators"
    chart_height = 500 + (180 * (subplot_rows - 1))

    fig.update_layout(
        title=dict(
            text=f"{title_tickers} - {period} - {interval} - {chart_type.upper()} - [{indicators_str}]",
            font=dict(size=14, color="#E0E0E0"),
            x=0.02,
        ),
        template="plotly_dark",
        paper_bgcolor="#0D1117",
        plot_bgcolor="#161B22",
        font=dict(family="Inter, Arial, sans-serif", color="#E0E0E0"),
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            bgcolor="rgba(13,17,23,0.8)",
            bordercolor="#30363D",
            borderwidth=1,
            font=dict(size=11),
        ),
        height=chart_height,
        margin=dict(l=60, r=40, t=60, b=40),
        hovermode="x unified",
    )

    for row in range(1, subplot_rows + 1):
        fig.update_xaxes(
            showgrid=True,
            gridcolor="#21262D",
            gridwidth=1,
            showline=True,
            linecolor="#30363D",
            row=row,
            col=1,
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor="#21262D",
            gridwidth=1,
            showline=True,
            linecolor="#30363D",
            row=row,
            col=1,
        )

    for indicator in ("returns", "volatility", "drawdown"):
        if indicator in row_map:
            fig.update_yaxes(ticksuffix="%", row=row_map[indicator], col=1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    safe_tickers = _safe_filename_part("_".join(tickers))
    safe_period = _safe_filename_part(period)
    safe_interval = _safe_filename_part(interval)
    filename = f"chart_{safe_tickers}_{safe_period}_{safe_interval}_{timestamp}.html"
    filepath = os.path.join(CHARTS_DIR, filename)

    fig.write_html(
        filepath,
        include_plotlyjs="cdn",
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    )

    return {
        "success": True,
        "filepath": filepath,
        "filename": filename,
        "tickers": tickers,
        "period": period,
        "interval": interval,
        "chart_type": chart_type,
        "indicators": indicators,
        "summary": summary,
        "data_source": data_source,
    }
