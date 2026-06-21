# Demo Requests

This file documents example natural-language requests and the expected behavior of the Stock Chart Visualization Agent.

## 1. Single Ticker Candlestick Chart With MA and Volume

User request:

```text
AAPL 1mo daily candlestick chart with MA and volume
```

Expected behavior:

- Extract ticker `AAPL`
- Use `period=1mo`
- Use `interval=1d`
- Use `chart_type=candle`
- Use `indicators=ma,volume`
- Generate an interactive HTML chart
- Return summary metrics

## 2. Single Ticker With RSI, Volatility, and Drawdown

User request:

```text
TSLA 3mo daily chart with RSI, volatility, and drawdown
```

Expected behavior:

- Extract ticker `TSLA`
- Use `period=3mo`
- Use `interval=1d`
- Use `indicators=rsi,volatility,drawdown`
- Generate RSI, rolling volatility, and drawdown subplots
- Return summary metrics

## 3. Multi-Ticker Normalized Comparison

User request:

```text
Compare AAPL, MSFT, GOOGL 1y performance with normalized line chart
```

Expected behavior:

- Extract tickers `AAPL`, `MSFT`, `GOOGL`
- Use `period=1y`
- Use `interval=1d`
- Force `chart_type=line`
- Use `indicator=normalized`
- Show normalized price comparison from base 100

## 4. Short-Period Intraday Returns and Volume

User request:

```text
NVDA 5d 1h chart with returns and volume
```

Expected behavior:

- Extract ticker `NVDA`
- Use `period=5d`
- Use `interval=1h`
- Use `indicators=returns,volume`
- Generate returns and volume subplots

## 5. Invalid Ticker Handling

User request:

```text
INVALIDTICKER 1mo daily chart
```

Expected behavior:

- Try to fetch data
- Return a clear no-data or invalid ticker message
- Suggest checking the ticker symbol

## 6. Interval-Period Mismatch Handling

User request:

```text
AAPL 1mo 1m chart
```

Expected behavior:

- Detect that `1m` interval is incompatible with `1mo` period
- Explain that minute intervals require short periods such as `1d` or `5d`
- Suggest changing either period or interval

## 7. Finance Advice Boundary

User request:

```text
Should I buy AAPL now?
```

Expected behavior:

- Do not provide financial advice
- Explain that the tool is for visualization and exploratory analysis only
- Offer to generate a chart with relevant indicators such as returns, volatility, drawdown, or RSI
