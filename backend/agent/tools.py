import os
from langchain_core.tools import tool
from backend.utils.chart_generator import create_chart, validate_interval_period


@tool
def generate_stock_chart(
    tickers: str,
    period: str,
    interval: str,
    chart_type: str = "candle",
    indicators: str = "",
) -> str:
    """
    주식 차트를 생성하고 인터랙티브 HTML 파일로 저장합니다.

    Args:
        tickers: 콤마로 구분된 티커 심볼 (예: "AAPL" 또는 "AAPL,MSFT")
        period: 조회 기간 - 1d/5d/1mo/3mo/6mo/1y/2y/5y/ytd/max
        interval: 캔들 간격 - 1m/5m/15m/30m/60m/1h/1d/1wk/1mo
        chart_type: 차트 종류 - "candle" 또는 "line"
        indicators: 지표 (콤마 구분) - "ma", "rsi", "volume" 또는 조합 "ma,rsi,volume"

    Returns:
        성공 시 차트 정보, 실패 시 에러 메시지
    """
    # interval-period 유효성 검사
    validation_error = validate_interval_period(interval, period)
    if validation_error:
        return validation_error

    # 파라미터 파싱
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    indicator_list = [i.strip().lower() for i in indicators.split(",") if i.strip()]

    if not ticker_list:
        return "❌ 티커 심볼이 없습니다. 예: AAPL, MSFT, TSLA"

    # 멀티 티커는 line 차트 강제
    if len(ticker_list) > 1 and chart_type == "candle":
        chart_type = "line"

    # 차트 생성
    result = create_chart(
        tickers=ticker_list,
        period=period,
        interval=interval,
        chart_type=chart_type,
        indicators=indicator_list,
    )

    if not result["success"]:
        return result["error"]

    indicators_display = ", ".join(indicator_list).upper() if indicator_list else "없음"
    return (
        f"✅ **차트 생성 완료!**\n\n"
        f"- 📊 티커: `{', '.join(ticker_list)}`\n"
        f"- 📅 기간: `{period}`\n"
        f"- ⏱️ 인터벌: `{interval}`\n"
        f"- 🕯️ 차트 유형: `{chart_type}`\n"
        f"- 📈 지표: `{indicators_display}`\n"
        f"- 💾 파일: `{result['filename']}`\n\n"
        f"CHART_FILE:{result['filename']}"
    )