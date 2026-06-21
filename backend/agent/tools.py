from langchain_core.tools import tool

from backend.utils.chart_generator import create_chart, validate_interval_period


SUPPORTED_INDICATORS = {
    "ma",
    "rsi",
    "volume",
    "returns",
    "volatility",
    "drawdown",
    "normalized",
}


def _format_number(value, suffix: str = "") -> str:
    """Format a numeric summary value, falling back to N/A."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def _format_summary(summary: dict) -> str:
    """Build a concise summary section from create_chart output."""
    if not summary:
        return ""

    lines = ["**Summary**"]
    for ticker, metrics in summary.items():
        metrics = metrics or {}
        latest_close = _format_number(metrics.get("latest_close"))
        total_return = _format_number(metrics.get("total_return_pct"), "%")
        max_drawdown = _format_number(metrics.get("max_drawdown_pct"), "%")
        volatility = _format_number(metrics.get("realized_volatility_pct"), "%")
        lines.append(
            f"- `{ticker}`: close {latest_close}, return {total_return}, "
            f"max drawdown {max_drawdown}, volatility {volatility}"
        )

    return "\n".join(lines)


@tool
def generate_stock_chart(
    tickers: str,
    period: str,
    interval: str,
    chart_type: str = "candle",
    indicators: str = "",
) -> str:
    """
    Generate an interactive stock chart and save it as an HTML file.

    Args:
        tickers: Comma-separated ticker symbols, e.g. "AAPL" or "AAPL,MSFT".
        period: Lookback period - 1d/5d/1mo/3mo/6mo/1y/2y/5y/ytd/max.
        interval: Candle interval - 1m/5m/15m/30m/60m/1h/1d/1wk/1mo.
        chart_type: Chart type - "candle" or "line".
        indicators: Comma-separated indicators. Supported values:
            ma = moving averages,
            rsi = relative strength index,
            volume = volume bars,
            returns = simple percentage returns,
            volatility = rolling 20-period annualized volatility,
            drawdown = drawdown from running high,
            normalized = relative price performance from a base value of 100.

    Returns:
        Chart information on success, or an error message on failure.
    """
    period = period.strip().lower()
    interval = interval.strip().lower()
    chart_type = chart_type.strip().lower()
    if chart_type == "candlestick":
        chart_type = "candle"

    validation_error = validate_interval_period(interval, period)
    if validation_error:
        return validation_error

    ticker_list = [ticker.strip().upper() for ticker in tickers.split(",") if ticker.strip()]
    parsed_indicators = [
        indicator.strip().lower()
        for indicator in indicators.split(",")
        if indicator.strip()
    ]
    indicator_list = list(
        dict.fromkeys(
            indicator
            for indicator in parsed_indicators
            if indicator in SUPPORTED_INDICATORS
        )
    )

    if not ticker_list:
        return "❌ 티커 심볼이 없습니다. 예: AAPL, MSFT, TSLA"

    if chart_type not in {"candle", "line"}:
        chart_type = "candle" if len(ticker_list) == 1 else "line"

    if (len(ticker_list) > 1 or "normalized" in indicator_list) and chart_type == "candle":
        chart_type = "line"

    result = create_chart(
        tickers=ticker_list,
        period=period,
        interval=interval,
        chart_type=chart_type,
        indicators=indicator_list,
    )

    if not result["success"]:
        return result["error"]

    indicators_display = ", ".join(indicator_list).upper() if indicator_list else "None"
    summary_text = _format_summary(result.get("summary", {}))
    summary_block = f"\n\n{summary_text}\n" if summary_text else "\n"
    data_note = (
        "\n- Data source: `demo fallback` (yfinance was unavailable locally)"
        if result.get("data_source") == "demo"
        else ""
    )

    return (
        f"**Chart generated!**\n\n"
        f"- Tickers: `{', '.join(ticker_list)}`\n"
        f"- Period: `{period}`\n"
        f"- Interval: `{interval}`\n"
        f"- Chart type: `{chart_type}`\n"
        f"- Indicators: `{indicators_display}`\n"
        f"- File: `{result['filename']}`"
        f"{data_note}"
        f"{summary_block}\n"
        f"CHART_FILE:{result['filename']}"
    )
