import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── 페이지 설정 ────────────────────────────────────────────────────
st.set_page_config(
    page_title="📈 Stock Chart Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS 스타일 ─────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* 전체 배경 */
    .stApp { background-color: #0D1117; color: #E0E0E0; }
    
    /* 채팅 메시지 */
    .user-msg {
        background: #1C2128; border-left: 3px solid #00D4FF;
        padding: 12px 16px; border-radius: 8px; margin: 8px 0;
    }
    .agent-msg {
        background: #161B22; border-left: 3px solid #26A69A;
        padding: 12px 16px; border-radius: 8px; margin: 8px 0;
    }
    
    /* 차트 컨테이너 */
    .chart-container {
        border: 1px solid #30363D; border-radius: 10px;
        overflow: hidden; margin: 12px 0;
    }
    
    /* 사이드바 */
    .css-1d391kg { background-color: #161B22; }
    
    /* 버튼 */
    .stButton>button {
        background: #21262D; border: 1px solid #30363D;
        color: #E0E0E0; border-radius: 6px;
    }
    .stButton>button:hover { background: #30363D; border-color: #00D4FF; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── 세션 상태 초기화 ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chart_files" not in st.session_state:
    st.session_state.chart_files = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())[:8]


# ── 헬퍼 함수 ─────────────────────────────────────────────────────
def send_message(user_input: str) -> dict:
    """백엔드 API에 메시지 전송"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={
                "message": user_input,
                "session_id": st.session_state.session_id,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "response": "❌ 백엔드 서버에 연결할 수 없습니다. `uvicorn backend.main:app --reload` 를 실행했는지 확인하세요.",
            "chart_files": [],
            "error": "Connection error",
        }
    except Exception as e:
        return {
            "response": f"❌ 오류 발생: {str(e)}",
            "chart_files": [],
            "error": str(e),
        }


def display_chart(filename: str):
    """HTML 차트를 iframe으로 표시"""
    chart_url = f"{BACKEND_URL}/charts/{filename}"
    # iframe으로 차트 임베드
    iframe_html = f"""
    <div class="chart-container">
        <iframe 
            src="{chart_url}" 
            width="100%" 
            height="550px" 
            frameborder="0"
            scrolling="no"
            style="border: none; background: #0D1117;"
        ></iframe>
    </div>
    """
    st.markdown(iframe_html, unsafe_allow_html=True)

    # 다운로드 링크도 제공
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown(f"[🔗 새 탭에서 열기]({chart_url})", unsafe_allow_html=False)


def clear_conversation():
    """대화 초기화"""
    st.session_state.messages = []
    st.session_state.chart_files = []
    try:
        requests.delete(f"{BACKEND_URL}/session/{st.session_state.session_id}")
    except:
        pass


# ── 사이드바 ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Stock Chart Agent")
    st.caption(
        "자연어 요청으로 인터랙티브 주식 시계열 차트를 생성합니다. "
        "시각화와 탐색적 분석용이며, 금융 조언이 아닙니다."
    )
    st.markdown("---")

    # 서버 상태 체크
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=3).json()
        st.success("🟢 서버 연결됨")
    except:
        st.error("🔴 서버 연결 안됨")
        st.caption(f"서버 URL: {BACKEND_URL}")

    st.markdown("---")
    st.markdown("### 💡 예시 요청")
    
    examples = [
        "AAPL 1개월 일봉 캔들차트 MA랑 거래량 포함",
        "TSLA 3개월 일봉 RSI, 변동성, drawdown 보여줘",
        "AAPL, MSFT, GOOGL 1년 수익률 비교 normalized 라인차트",
        "NVDA 5일 1시간봉 returns랑 volume 포함",
        "삼성전자(005930.KS) 6개월 일봉 MA, RSI 포함",
    ]
    
    for example in examples:
        if st.button(example, use_container_width=True, key=f"ex_{example[:15]}"):
            st.session_state.pending_input = example

    st.markdown("---")
    st.markdown("### ⚙️ 파라미터 참고")
    st.markdown("""
    **Period:** `1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y`
    
    **Interval:** `1m` `5m` `15m` `1h` `1d` `1wk` `1mo`
    
    **⚠️ 주의:** 분봉(1m~60m)은 최대 7일만 가능
    
    **Indicators**
    
    - `ma`: moving averages
    - `rsi`: RSI
    - `volume`: volume bars
    - `returns`: simple percentage returns
    - `volatility`: rolling volatility
    - `drawdown`: drawdown from running maximum
    - `normalized`: normalized comparison from base 100
    """)
    
    st.markdown("---")

    # 생성된 차트 목록
    try:
        charts_data = requests.get(f"{BACKEND_URL}/charts", timeout=3).json()
        charts = charts_data.get("charts", [])
        if charts:
            st.markdown("### 📁 생성된 차트")
            for chart in charts[:10]:  # 최근 10개만
                st.markdown(f"[📊 {chart}]({BACKEND_URL}/charts/{chart})")
    except:
        pass

    st.markdown("---")
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        clear_conversation()
        st.rerun()

    st.caption(f"Session ID: {st.session_state.session_id}")


# ── 메인 영역 ──────────────────────────────────────────────────────
st.markdown("## 💬 Stock Chart Visualization Agent")
st.markdown("주식 차트를 자연어로 요청하세요. 인터랙티브 HTML 차트를 생성해드립니다.")
st.markdown("---")

# 대화 기록 표시
chat_container = st.container()
with chat_container:
    if not st.session_state.messages:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px; color: #6B7280;">
                <h3>👋 안녕하세요!</h3>
                <p>왼쪽 사이드바의 예시를 클릭하거나 아래에 직접 입력해보세요.</p>
                <p>예: <code>"AAPL 1개월 일봉 캔들차트에 MA와 거래량 추가해줘"</code></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-msg">👤 <strong>You</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="agent-msg">🤖 <strong>Agent</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
            # 차트 파일이 있으면 iframe으로 표시
            if "charts" in msg and msg["charts"]:
                for chart_file in msg["charts"]:
                    display_chart(chart_file)


# ── 입력창 ─────────────────────────────────────────────────────────
st.markdown("---")

# 사이드바 예시 버튼 클릭 처리
pending = st.session_state.pop("pending_input", None)

user_input = st.chat_input(
    "주식 차트 요청을 입력하세요... (예: AAPL 3개월 일봉 캔들 MA포함)",
    key="chat_input",
)

# 실제 입력 또는 예시 버튼 처리
final_input = user_input or pending

if final_input:
    # 유저 메시지 저장
    st.session_state.messages.append({"role": "user", "content": final_input})

    # 에이전트 응답 받기
    with st.spinner("🤔 Agent 처리 중..."):
        result = send_message(final_input)

    # 에이전트 응답 저장
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["response"],
            "charts": result.get("chart_files", []),
        }
    )

    # 차트 파일 목록 업데이트
    for cf in result.get("chart_files", []):
        if cf not in st.session_state.chart_files:
            st.session_state.chart_files.append(cf)

    st.rerun()
