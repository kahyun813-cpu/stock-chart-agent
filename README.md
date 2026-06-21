# Natural-Language Stock Time-Series Visualization Agent

## Overview

Natural-Language Stock Time-Series Visualization Agent converts natural-language stock chart requests into interactive time-series visualizations. It uses a LangGraph/LangChain agent to extract chart parameters, a FastAPI backend, a Streamlit frontend, yfinance market data, pandas analysis utilities, and Plotly HTML charts. The project supports exploratory visualization of price movement, indicators, returns, volatility, and drawdown. It is not an investment recommendation system, trading bot, or price forecasting tool, and it does not provide financial advice.

## Key Features

- Natural-language parameter extraction
- Ticker, period, interval, chart type, and indicator handling
- Candlestick and line charts
- Multi-ticker comparison
- Normalized price comparison from base 100
- Moving averages, RSI, and volume
- Simple returns, rolling volatility, and drawdown
- FastAPI backend and Streamlit frontend
- Session-based chat history
- HTML chart generation and iframe rendering
- Error handling for invalid tickers, missing data, and interval-period mismatch
- Lightweight tests for reusable analysis utilities

## Architecture

```text
User request
-> Streamlit frontend
-> FastAPI /chat endpoint
-> LangGraph agent
-> generate_stock_chart tool
-> yfinance data fetching
-> pandas analysis utilities
-> Plotly HTML chart generation
-> FastAPI chart file serving
-> Streamlit iframe rendering
```

Component overview:

- `frontend/app.py`: Streamlit chat UI, sidebar examples, backend requests, and iframe chart rendering.
- `backend/main.py`: FastAPI app with `/chat`, `/charts/{filename}`, `/charts`, `/health`, and session-clearing endpoints.
- `backend/agent/graph.py`: LangGraph workflow that calls the LLM, routes tool calls, and tracks generated chart files.
- `backend/agent/tools.py`: LangChain tool interface for chart generation, parameter cleanup, indicator filtering, and summary formatting.
- `backend/utils/chart_generator.py`: yfinance data fetching, Plotly chart creation, indicator subplot rendering, summaries, and HTML file output.
- `backend/utils/technical_analysis.py`: Pure pandas analysis functions for returns, volatility, drawdown, normalization, and summary metrics.
- `prompts/chart_agent.yaml`: System prompt that defines parameter extraction, indicator-selection rules, and safety boundaries.
- `scripts/demo_requests.md`: Documentation of demo prompts and expected agent behavior.
- `tests/test_technical_analysis.py`: pytest coverage for reusable analysis utilities using synthetic data.

## Tech Stack

- Python
- FastAPI
- Streamlit
- LangGraph
- LangChain
- OpenAI API
- yfinance
- pandas
- Plotly
- pytest

## Supported Parameters

| Parameter | Supported values |
| --- | --- |
| Period | `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `ytd`, `max` |
| Interval | `1m`, `5m`, `15m`, `30m`, `60m`, `1h`, `1d`, `1wk`, `1mo` |
| Chart type | `candle`, `line` |
| Indicators | `ma`, `rsi`, `volume`, `returns`, `volatility`, `drawdown`, `normalized` |

Notes:

- Minute-level intervals should be used with short periods such as `1d` or `5d`.
- Multi-ticker and normalized comparisons use line charts.

## Example Requests

```text
AAPL 1개월 일봉 캔들차트 MA랑 거래량 포함
```

Creates a single-ticker candlestick chart with moving averages and volume.

```text
TSLA 3개월 일봉 RSI, 변동성, drawdown 보여줘
```

Creates a single-ticker chart with RSI, rolling volatility, and drawdown subplots.

```text
AAPL, MSFT, GOOGL 1년 수익률 비교 normalized 라인차트
```

Creates a multi-ticker normalized line comparison from base 100.

```text
NVDA 5일 1시간봉 returns랑 volume 포함
```

Creates a short-period intraday chart with returns and volume.

```text
삼성전자(005930.KS) 6개월 일봉 MA, RSI 포함
```

Creates a Korean stock chart with moving averages and RSI.

```text
AAPL 1개월 1분봉 차트 그려줘
```

Should explain the interval-period mismatch and suggest using a shorter period or a larger interval.

```text
AAPL 지금 사도 돼?
```

The system should not provide financial advice. It should explain that the app is for visualization and exploratory analysis only, and offer to generate a chart with indicators such as returns, volatility, drawdown, or RSI.

## What I Implemented

- Built a Streamlit frontend for chat-style user input and HTML chart rendering.
- Built a FastAPI backend with `/chat`, `/charts/{filename}`, `/charts`, and `/health` endpoints.
- Implemented a LangGraph agent that calls a chart-generation tool.
- Implemented yfinance-based OHLCV data fetching.
- Implemented Plotly chart generation for candlestick, line, RSI, volume, returns, volatility, drawdown, and normalized comparison.
- Added reusable pandas analysis functions for returns, rolling volatility, drawdown, normalized prices, and summary metrics.
- Added validation for interval-period mismatch.
- Added pytest tests for the analysis utility functions.

## Analysis Utilities

The analysis utilities are intentionally separated from yfinance and Plotly so they can be tested independently.

- `calculate_log_returns`: Computes log returns using `log(C_t / C_{t-1})`.
- `calculate_simple_returns`: Computes percentage returns using `pct_change()`.
- `calculate_rolling_volatility`: Computes rolling volatility from log returns, with optional annualization.
- `calculate_drawdown`: Computes drawdown from the cumulative running maximum.
- `normalize_price`: Normalizes the first valid close value to a base value, defaulting to 100.
- `summarize_price_series`: Produces summary metrics such as latest close, total return, max drawdown, realized volatility, average volume, date range, and observation count.

## Testing

Tests are in `tests/test_technical_analysis.py`. They use synthetic data and do not call yfinance. They test returns, log returns, rolling volatility, drawdown, normalized price, and summary metrics.

Run syntax checks and tests:

```bash
python -m py_compile backend/utils/technical_analysis.py
pytest
```

Current test result:

```text
7 passed
```

## How to Run

1. Create and activate a virtual environment.

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

2. Install requirements.

```bash
pip install -r requirements.txt
```

3. Create a `.env` file.

```env
OPENAI_API_KEY=your_api_key_here
BACKEND_URL=http://localhost:8000
CHARTS_DIR=charts
```

4. Run the backend.

```bash
uvicorn backend.main:app --reload
```

5. Run the frontend in another terminal.

```bash
streamlit run frontend/app.py
```

## Project Structure

```text
stock-chart-agent/
|-- backend/
|   |-- agent/
|   |   |-- graph.py
|   |   |-- state.py
|   |   `-- tools.py
|   |-- main.py
|   `-- utils/
|       |-- chart_generator.py
|       `-- technical_analysis.py
|-- frontend/
|   `-- app.py
|-- prompts/
|   `-- chart_agent.yaml
|-- scripts/
|   `-- demo_requests.md
|-- tests/
|   `-- test_technical_analysis.py
`-- README.md
```

## Limitations

- This project depends on yfinance data availability.
- Some tickers, markets, periods, or intervals may return no data.
- Minute-level data has strict lookback constraints.
- Rolling volatility is a simplified historical volatility measure and should not be treated as a full risk model.
- The app does not forecast prices.
- The app does not provide financial advice.
- In-memory session history resets when the backend restarts.
- Multi-ticker subplots can become visually crowded when many indicators are selected.

## Resume Bullet Suggestions

- Built an end-to-end natural-language stock time-series visualization agent using LangGraph, FastAPI, Streamlit, yfinance, pandas, and Plotly.
- Implemented interactive candlestick/line charts with moving averages, RSI, volume, normalized multi-ticker comparison, returns, rolling volatility, and drawdown.
- Added reusable pandas analysis utilities and pytest coverage for return, volatility, drawdown, normalization, and summary metric calculations.
