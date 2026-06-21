import os
import re
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

from backend.utils.technical_analysis import (
    calculate_drawdown,
    calculate_rolling_volatility,
    calculate_simple_returns,
    normalize_price,
    summarize_price_series,
)

CHARTS_DIR = os.getenv("CHARTS_DIR", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

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


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI(상대강도지수) 계산"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def validate_interval_period(interval: str, period: str) -> Optional[str]:
    """
    interval과 period 조합이 유효한지 검증
    Returns: None if valid, error string if invalid
    """
    minute_intervals = ["1m", "5m", "15m", "30m", "60m"]
    valid_short_periods = ["1d", "5d", "7d"]

    if interval in minute_intervals and period not in valid_short_periods:
        return (
            f"⚠️ **Interval-Period Mismatch!**\n"
            f"`{interval}` 인터벌은 최대 7일 데이터만 지원합니다.\n\n"
            f"**해결 방법:**\n"
            f"- 옵션 1: period를 `5d` 또는 `7d`로 변경\n"
            f"- 옵션 2: interval을 `1h`, `1d`, `1wk`로 변경"
        )
    return None


def fetch_ticker_data(ticker: str, period: str, interval: str) -> tuple[pd.DataFrame, str]:
    """
    yfinance에서 주식 데이터 수집
    - yf.Ticker().history() 사용 (MultiIndex 문제 없음)
    
    Returns: (DataFrame, error_message)
    DataFrame이 비어있으면 error_message에 원인이 담김
    """
    try:
        # ✅ Ticker().history() 는 항상 깔끔한 단일 레벨 컬럼 반환
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)

        if df is None or df.empty:
            return pd.DataFrame(), (
                f"❌ `{ticker}` 에 대한 데이터가 없습니다.\n"
                f"- US 주식: `AAPL`, `MSFT`, `TSLA`, `NVDA`\n"
                f"- 한국 주식: `005930.KS` (삼성전자), `000660.KS` (SK하이닉스)\n"
                f"- ETF: `SPY`, `QQQ`, `ARKK`\n"
                f"- 티커 심볼과 기간/인터벌 조합을 확인해주세요."
            )

        # 컬럼 이름 정리 (혹시 대소문자 문제 방지)
        df.columns = [c.capitalize() for c in df.columns]

        # 필수 컬럼 존재 확인
        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return pd.DataFrame(), (
                f"❌ `{ticker}` 데이터에 필수 컬럼이 없습니다: {missing}\n"
                f"다른 기간이나 인터벌로 다시 시도해보세요."
            )

        return df, ""

    except Exception as e:
        return pd.DataFrame(), f"❌ `{ticker}` 데이터 수집 중 오류: {str(e)}"


def create_chart(
    tickers: list[str],
    period: str,
    interval: str,
    chart_type: str = "candle",
    indicators: list[str] = None,
) -> dict:
    """
    Plotly 인터랙티브 차트 생성 후 HTML 파일로 저장
    
    Returns:
        dict with keys: success (bool), filepath, filename, error
    """
    if indicators is None:
        indicators = []
    indicators = [indicator.strip().lower() for indicator in indicators if indicator]

    # 데이터 수집
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

    # 서브플롯 구조 결정
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
        subplot_titles.append("Rolling Volatility 20D (%)")
        row_map["volatility"] = subplot_rows
    if has_drawdown:
        subplot_rows += 1
        row_heights.append(0.16)
        subplot_titles.append("Drawdown (%)")
        row_map["drawdown"] = subplot_rows

    # Figure 생성
    fig = make_subplots(
        rows=subplot_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # 색상 팔레트
    line_colors = ["#00D4FF", "#FF6B6B", "#51CF66", "#FFE066", "#CC5DE8"]

    for idx, (ticker, df) in enumerate(stock_data.items()):
        color = line_colors[idx % len(line_colors)]

        # ── 메인 차트 (캔들스틱 or 라인) ──────────────────────────
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

        # ── 이동평균선 (MA) ────────────────────────────────────────
        if "ma" in indicators and not has_normalized:
            close = df["Close"]
            ma_configs = [
                (20, "#FF6B6B", "MA20"),
                (50, "#FFE066", "MA50"),
                (200, "#51CF66", "MA200"),
            ]
            for window, ma_color, ma_name in ma_configs:
                if len(df) >= window:
                    ma_values = close.rolling(window=window).mean()
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

        # ── RSI ───────────────────────────────────────────────────
        if has_rsi:
            close = df["Close"]
            rsi_values = calculate_rsi(close)
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
            # 과매수/과매도 라인
            fig.add_hline(
                y=70, line=dict(color="#EF5350", dash="dash", width=1), opacity=0.6,
                row=row_map["rsi"], col=1,
            )
            fig.add_hline(
                y=30, line=dict(color="#26A69A", dash="dash", width=1), opacity=0.6,
                row=row_map["rsi"], col=1,
            )
            fig.update_yaxes(range=[0, 100], row=row_map["rsi"], col=1)

        # ── 거래량 (Volume) ────────────────────────────────────────
        if has_volume:
            close = df["Close"].values
            vol_colors = []
            for i in range(len(close)):
                if i == 0:
                    vol_colors.append("#26A69A")
                elif close[i] >= close[i - 1]:
                    vol_colors.append("#26A69A")
                else:
                    vol_colors.append("#EF5350")

            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df["Volume"],
                    name=f"{ticker} Volume" if len(tickers) > 1 else "Volume",
                    marker=dict(color=vol_colors, opacity=0.8),
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

    # ── 레이아웃 설정 ──────────────────────────────────────────────
    title_tickers = " | ".join(tickers)
    indicators_str = ", ".join(indicators).upper() if indicators else "No Indicators"
    chart_height = 500 + (180 * (subplot_rows - 1))

    fig.update_layout(
        title=dict(
            text=f"📈 {title_tickers}  ·  {period}  ·  {interval}  ·  {chart_type.upper()}  ·  [{indicators_str}]",
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

    # 그리드 스타일
    for i in range(1, subplot_rows + 1):
        fig.update_xaxes(
            showgrid=True, gridcolor="#21262D", gridwidth=1,
            showline=True, linecolor="#30363D", row=i, col=1,
        )
        fig.update_yaxes(
            showgrid=True, gridcolor="#21262D", gridwidth=1,
            showline=True, linecolor="#30363D", row=i, col=1,
        )

    for indicator in ("returns", "volatility", "drawdown"):
        if indicator in row_map:
            fig.update_yaxes(ticksuffix="%", row=row_map[indicator], col=1)

    # ── HTML 파일로 저장 ───────────────────────────────────────────
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
    }
