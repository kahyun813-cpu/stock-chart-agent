import re

from backend.agent.tools import generate_stock_chart


TICKER_ALIASES = {
    "tesla": "TSLA",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "nvidia": "NVDA",
    "samsung": "005930.KS",
    "sk hynix": "000660.KS",
}

NON_TICKER_TOKENS = {
    "MA",
    "RSI",
    "VOLUME",
    "RETURN",
    "RETURNS",
    "VOLATILITY",
    "DRAWDOWN",
    "NORMALIZED",
    "LINE",
    "CANDLE",
}


def _extract_tickers(message: str) -> list[str]:
    tickers = []
    upper_matches = re.findall(r"\b\d{6}\.KS\b|\b[A-Z]{1,6}(?:\.[A-Z]{1,3})?\b", message)

    for ticker in upper_matches:
        if ticker not in NON_TICKER_TOKENS and ticker not in tickers:
            tickers.append(ticker)

    lowered = message.lower()
    for alias, ticker in TICKER_ALIASES.items():
        if alias in lowered and ticker not in tickers:
            tickers.append(ticker)

    return tickers


def _extract_period(message: str) -> str:
    lowered = message.lower().replace(" ", "")
    patterns = [
        (r"5years?|5yrs?|5y", "5y"),
        (r"2years?|2yrs?|2y", "2y"),
        (r"1years?|1yrs?|oneyear|1y", "1y"),
        (r"6months?|6mos?|6mo", "6mo"),
        (r"3months?|3mos?|3mo", "3mo"),
        (r"1months?|1mos?|onemonth|1mo", "1mo"),
        (r"5days?|5d", "5d"),
        (r"1days?|oneday|1d", "1d"),
        (r"ytd", "ytd"),
        (r"max", "max"),
    ]
    for pattern, period in patterns:
        if re.search(pattern, lowered):
            return period
    return "1mo"


def _extract_interval(message: str) -> str:
    lowered = message.lower().replace(" ", "")
    patterns = [
        (r"30m|30min", "30m"),
        (r"15m|15min", "15m"),
        (r"5m|5min", "5m"),
        (r"1m|1min", "1m"),
        (r"1h|1hour|hourly", "1h"),
        (r"1d|daily", "1d"),
        (r"1wk|weekly", "1wk"),
        (r"1mo|monthly", "1mo"),
    ]
    for pattern, interval in patterns:
        if re.search(pattern, lowered):
            return interval
    return "1d"


def _extract_chart_type(message: str, tickers: list[str], indicators: list[str]) -> str:
    lowered = message.lower()
    if "normalized" in indicators or len(tickers) > 1:
        return "line"
    if any(word in lowered for word in ["line", "line chart"]):
        return "line"
    return "candle"


def _extract_indicators(message: str) -> list[str]:
    lowered = message.lower()
    indicators = []
    keyword_map = [
        ("ma", ["ma", "moving average", "moving averages"]),
        ("rsi", ["rsi", "overbought", "oversold"]),
        ("volume", ["volume", "trading volume"]),
        ("returns", ["returns", "return", "performance change"]),
        ("volatility", ["volatility", "fluctuation", "risk", "stability", "variability"]),
        ("drawdown", ["drawdown", "decline from peak", "downside", "loss from high"]),
        ("normalized", ["normalized", "normalize", "comparison", "relative performance"]),
    ]

    for indicator, keywords in keyword_map:
        if any(keyword in lowered for keyword in keywords):
            indicators.append(indicator)

    return list(dict.fromkeys(indicators))


def _is_financial_advice_request(message: str) -> bool:
    lowered = message.lower()
    advice_keywords = [
        "buy now",
        "should i buy",
        "should i sell",
        "sell now",
        "is it a good buy",
        "investment advice",
    ]
    return any(keyword in lowered for keyword in advice_keywords)


def run_local_chart_fallback(message: str) -> dict:
    """Generate a chart response without calling an LLM."""
    if _is_financial_advice_request(message):
        return {
            "response": (
                "I can't provide financial advice or tell you whether to buy or sell. "
                "This app is for visualization and exploratory analysis only. "
                "I can generate a chart with returns, volatility, drawdown, RSI, or volume instead."
            ),
            "chart_files": [],
            "error": "",
        }

    tickers = _extract_tickers(message)
    if not tickers:
        return {
            "response": "Please include a ticker symbol, such as AAPL, TSLA, NVDA, or 005930.KS.",
            "chart_files": [],
            "error": "",
        }

    indicators = _extract_indicators(message)
    period = _extract_period(message)
    interval = _extract_interval(message)
    chart_type = _extract_chart_type(message, tickers, indicators)

    tool_response = generate_stock_chart.invoke(
        {
            "tickers": ",".join(tickers),
            "period": period,
            "interval": interval,
            "chart_type": chart_type,
            "indicators": ",".join(indicators),
        }
    )

    chart_files = []
    response_text = tool_response
    if "CHART_FILE:" in tool_response:
        response_text, marker = tool_response.split("CHART_FILE:", 1)
        filename = marker.strip().splitlines()[0]
        if filename:
            chart_files.append(filename)
        response_text = response_text.strip()

    return {
        "response": response_text,
        "chart_files": chart_files,
        "error": "",
    }
