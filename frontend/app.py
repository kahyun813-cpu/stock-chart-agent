import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Stock Chart Agent",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #0D1117; color: #E0E0E0; }

    .user-msg {
        background: #1C2128; border-left: 3px solid #00D4FF;
        padding: 12px 16px; border-radius: 8px; margin: 8px 0;
    }
    .agent-msg {
        background: #161B22; border-left: 3px solid #26A69A;
        padding: 12px 16px; border-radius: 8px; margin: 8px 0;
    }

    .chart-container {
        border: 1px solid #30363D; border-radius: 10px;
        overflow: hidden; margin: 12px 0;
    }

    .css-1d391kg { background-color: #161B22; }

    .stButton>button {
        background: #21262D; border: 1px solid #30363D;
        color: #E0E0E0; border-radius: 6px;
    }
    .stButton>button:hover { background: #30363D; border-color: #00D4FF; }
    </style>
    """,
    unsafe_allow_html=True,
)


if "messages" not in st.session_state:
    st.session_state.messages = []
if "chart_files" not in st.session_state:
    st.session_state.chart_files = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]


def send_message(user_input: str) -> dict:
    """Send a chat message to the backend API."""
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
            "response": (
                "Backend server is not reachable. Start it with "
                "`uvicorn backend.main:app --reload` or run `scripts/run_local.bat`."
            ),
            "chart_files": [],
            "error": "Connection error",
        }
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "chart_files": [],
            "error": str(e),
        }


def display_chart(filename: str) -> None:
    """Render a generated HTML chart inside an iframe."""
    chart_url = f"{BACKEND_URL}/charts/{filename}"
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

    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown(f"[Open chart in browser]({chart_url})", unsafe_allow_html=False)


def clear_conversation() -> None:
    """Clear local and backend session history."""
    st.session_state.messages = []
    st.session_state.chart_files = []
    try:
        requests.delete(f"{BACKEND_URL}/session/{st.session_state.session_id}")
    except Exception:
        pass


with st.sidebar:
    st.markdown("## Stock Chart Agent")
    st.caption(
        "Generate interactive stock time-series charts from natural-language requests. "
        "This app is for visualization and exploratory analysis only, not financial advice."
    )
    st.markdown("---")

    try:
        requests.get(f"{BACKEND_URL}/health", timeout=3).json()
        st.success("Backend connected")
    except Exception:
        st.error("Backend not connected")
        st.caption(f"Backend URL: {BACKEND_URL}")

    st.markdown("---")
    st.markdown("### Example Requests")

    examples = [
        "AAPL 1mo daily candlestick chart with MA and volume",
        "TSLA 3mo daily chart with RSI, volatility, and drawdown",
        "Compare AAPL, MSFT, GOOGL 1y performance with normalized line chart",
        "NVDA 5d 1h chart with returns and volume",
        "Samsung 005930.KS 6mo daily chart with MA and RSI",
    ]

    for example in examples:
        if st.button(example, use_container_width=True, key=f"ex_{example[:15]}"):
            st.session_state.pending_input = example

    st.markdown("---")
    st.markdown("### Parameter Reference")
    st.markdown(
        """
        **Period:** `1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y`

        **Interval:** `1m` `5m` `15m` `1h` `1d` `1wk` `1mo`

        **Note:** Minute intervals should be used with short periods such as `1d` or `5d`.

        **Indicators**

        - `ma`: moving averages
        - `rsi`: RSI
        - `volume`: volume bars
        - `returns`: simple percentage returns
        - `volatility`: rolling volatility
        - `drawdown`: drawdown from running maximum
        - `normalized`: normalized comparison from base 100
        """
    )

    st.markdown("---")

    try:
        charts_data = requests.get(f"{BACKEND_URL}/charts", timeout=3).json()
        charts = charts_data.get("charts", [])
        if charts:
            st.markdown("### Generated Charts")
            for chart in charts[:10]:
                st.markdown(f"[{chart}]({BACKEND_URL}/charts/{chart})")
    except Exception:
        pass

    st.markdown("---")
    if st.button("Clear conversation", use_container_width=True):
        clear_conversation()
        st.rerun()

    st.caption(f"Session ID: {st.session_state.session_id}")


st.markdown("## Stock Chart Visualization Agent")
st.markdown("Request an interactive stock chart in natural language.")
st.markdown("---")

chat_container = st.container()
with chat_container:
    if not st.session_state.messages:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px; color: #6B7280;">
                <h3>Welcome</h3>
                <p>Choose an example from the sidebar or type a request below.</p>
                <p>Example: <code>AAPL 1mo daily candlestick chart with MA and volume</code></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-msg"><strong>You</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="agent-msg"><strong>Agent</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
            if "charts" in msg and msg["charts"]:
                for chart_file in msg["charts"]:
                    display_chart(chart_file)


st.markdown("---")

pending = st.session_state.pop("pending_input", None)

user_input = st.chat_input(
    "Enter a stock chart request, e.g. AAPL 3mo daily candle with MA",
    key="chat_input",
)

final_input = user_input or pending

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})

    with st.spinner("Agent is working..."):
        result = send_message(final_input)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["response"],
            "charts": result.get("chart_files", []),
        }
    )

    for chart_file in result.get("chart_files", []):
        if chart_file not in st.session_state.chart_files:
            st.session_state.chart_files.append(chart_file)

    st.rerun()
