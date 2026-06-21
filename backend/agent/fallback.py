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
    "삼성전자": "005930.KS",
    "삼성": "005930.KS",
    "sk하이닉스": "000660.KS",
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
        (r"5년|5years?|5yrs?", "5y"),
        (r"2년|2years?|2yrs?", "2y"),
        (r"1년|1years?|1yrs?|oneyear", "1y"),
        (r"6개월|6months?|6mos?", "6mo"),
        (r"3개월|3months?|3mos?", "3mo"),
        (r"1개월|1months?|1mos?|onemonth", "1mo"),
        (r"5일|5days?", "5d"),
        (r"1일|1days?|oneday", "1d"),
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
        (r"30분봉|30m|30min", "30m"),
        (r"15분봉|15m|15min", "15m"),
        (r"5분봉|5m|5min", "5m"),
        (r"1분봉|1m|1min", "1m"),
        (r"1시간봉|시간봉|1h|1hour|hourly", "1h"),
        (r"일봉|1d|daily", "1d"),
        (r"주봉|1wk|weekly", "1wk"),
        (r"월봉|1mo|monthly", "1mo"),
    ]
    for pattern, interval in patterns:
        if re.search(pattern, lowered):
            return interval
    return "1d"


def _extract_chart_type(message: str, tickers: list[str], indicators: list[str]) -> str:
    lowered = message.lower()
    if "normalized" in indicators or len(tickers) > 1:
        return "line"
    if any(word in lowered for word in ["line", "라인", "선차트"]):
        return "line"
    return "candle"


def _extract_indicators(message: str) -> list[str]:
    lowered = message.lower()
    indicators = []
    keyword_map = [
        ("ma", ["ma", "moving average", "moving averages", "이동평균", "이평"]),
        ("rsi", ["rsi", "과매수", "과매도"]),
        ("volume", ["volume", "거래량"]),
        ("returns", ["returns", "return", "수익률", "변동률"]),
        ("volatility", ["volatility", "변동성", "fluctuation", "risk", "리스크"]),
        ("drawdown", ["drawdown", "낙폭", "하락폭", "고점 대비"]),
        ("normalized", ["normalized", "normalize", "비교", "상대", "relative performance"]),
    ]

    for indicator, keywords in keyword_map:
        if any(keyword in lowered for keyword in keywords):
            indicators.append(indicator)

    return list(dict.fromkeys(indicators))


def _is_financial_advice_request(message: str) -> bool:
    lowered = message.lower()
    advice_keywords = [
        "사도 돼",
        "살까",
        "매수",
        "팔까",
        "매도",
        "buy now",
        "should i buy",
        "should i sell",
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
