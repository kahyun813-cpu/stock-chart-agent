import os
import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from backend.agent.state import AgentState
from backend.agent.tools import generate_stock_chart

load_dotenv()

# ── 프롬프트 로드 ──────────────────────────────────────────────────
def load_prompts() -> dict:
    prompts_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "prompts", "chart_agent.yaml"
    )
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ── LLM 설정 ──────────────────────────────────────────────────────
def create_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",       # 저렴하고 빠름. gpt-4o로 바꿔도 됨
        temperature=0,
        streaming=True,
    )

# ── 도구 목록 ─────────────────────────────────────────────────────
tools = [generate_stock_chart]

# ── 에이전트 노드 ──────────────────────────────────────────────────
def agent_node(state: AgentState) -> AgentState:
    """LLM이 메시지를 읽고 도구 호출 여부를 결정"""
    prompts = load_prompts()
    system_msg = SystemMessage(content=prompts["system_prompt"])

    llm = create_llm()
    llm_with_tools = llm.bind_tools(tools)

    messages = [system_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


# ── 도구 실행 후 차트 파일 추적 ────────────────────────────────────
def track_chart_files(state: AgentState) -> AgentState:
    """도구 실행 결과에서 생성된 차트 파일명 추출"""
    chart_files = list(state.get("chart_files", []))
    last_error = ""

    for msg in reversed(state["messages"]):
        # ToolMessage 타입 확인
        if hasattr(msg, "content") and isinstance(msg.content, str):
            if "CHART_FILE:" in msg.content:
                # 파일명 추출
                parts = msg.content.split("CHART_FILE:")
                if len(parts) > 1:
                    filename = parts[1].strip().split("\n")[0]
                    if filename not in chart_files:
                        chart_files.append(filename)
            elif msg.content.startswith("❌") or msg.content.startswith("⚠️"):
                last_error = msg.content
        break  # 가장 최근 메시지만 확인

    return {"chart_files": chart_files, "last_error": last_error}


# ── 그래프 빌드 ────────────────────────────────────────────────────
def build_graph():
    """LangGraph 에이전트 그래프 생성"""
    tool_node = ToolNode(tools)

    builder = StateGraph(AgentState)

    # 노드 추가
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_node("track_charts", track_chart_files)

    # 엣지 연결
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition,             # 도구 호출이 필요하면 tools로, 아니면 END로
    )
    builder.add_edge("tools", "track_charts")
    builder.add_edge("track_charts", "agent")

    return builder.compile()


# 전역 그래프 인스턴스 (앱 시작 시 한 번 빌드)
graph = build_graph()