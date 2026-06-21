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
AAPL 1mo daily candlestick chart with MA and volume
```

Creates a single-ticker candlestick chart with moving averages and volume.

```text
TSLA 3mo daily chart with RSI, volatility, and drawdown
```

Creates a single-ticker chart with RSI, rolling volatility, and drawdown subplots.
<img width="1278" height="673" alt="image" src="https://github.com/user-attachments/assets/06bf1125-90af-4b01-8ad4-184fe4916a53" />


```text
Compare AAPL, MSFT, GOOGL 1y performance with normalized line chart
```

Creates a multi-ticker normalized line comparison from base 100.

```text
NVDA 5d 1h chart with returns and volume
```

Creates a short-period intraday chart with returns and volume.

```text
Samsung 005930.KS 6mo daily chart with MA and RSI
```

Creates a Korean stock chart with moving averages and RSI.

```text
AAPL 1mo 1m chart
```

Should explain the interval-period mismatch and suggest using a shorter period or a larger interval.

```text
Should I buy AAPL now?
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
BACKEND_URL=http://127.0.0.1:8000
CHARTS_DIR=charts
LANGCHAIN_TRACING_V2=false
```

4. Run locally from VSCode or PowerShell with one command.

```bat
.\scripts\run_local.bat
```

This starts the FastAPI backend on `http://127.0.0.1:8000` and the Streamlit frontend on `http://127.0.0.1:8501`.

If your PowerShell execution policy allows local scripts, you can also run:

```powershell
.\scripts\run_local.ps1
```

5. Alternatively, run the backend manually.

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

6. Run the frontend manually in another terminal.

```bash
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

## Deployment Notes

The current implementation uses Streamlit and FastAPI as long-running local web services. That structure is best suited for platforms such as Render, Railway, Fly.io, or Streamlit Community Cloud.

For a Vercel deployment, the recommended next step is to migrate the Streamlit frontend to a Vercel-native frontend such as Next.js and keep the chart API as either:

- a separate hosted FastAPI backend, or
- serverless API routes adapted for Vercel's execution model.

This README describes the implemented local/full-stack prototype and avoids claiming a Vercel deployment that is not yet implemented.

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
|   |-- demo_requests.md
|   |-- run_local.bat
|   `-- run_local.ps1
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
