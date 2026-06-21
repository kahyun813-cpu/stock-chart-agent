import os

import yaml
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from backend.agent.state import AgentState
from backend.agent.tools import generate_stock_chart

load_dotenv()


def load_prompts() -> dict:
    """Load the chart agent prompt file."""
    prompts_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "prompts", "chart_agent.yaml"
    )
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_llm():
    """Create the chat model used by the LangGraph agent."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        streaming=True,
    )


tools = [generate_stock_chart]


def agent_node(state: AgentState) -> AgentState:
    """Ask the LLM whether to answer directly or call a tool."""
    prompts = load_prompts()
    system_msg = SystemMessage(content=prompts["system_prompt"])

    llm = create_llm()
    llm_with_tools = llm.bind_tools(tools)

    messages = [system_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


def track_chart_files(state: AgentState) -> AgentState:
    """Extract generated chart filenames from tool output."""
    chart_files = list(state.get("chart_files", []))
    last_error = ""

    for msg in reversed(state["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str):
            if "CHART_FILE:" in msg.content:
                parts = msg.content.split("CHART_FILE:")
                if len(parts) > 1:
                    filename = parts[1].strip().split("\n")[0]
                    if filename not in chart_files:
                        chart_files.append(filename)
            elif msg.content.startswith(("Error", "No ticker", "Could not", "Interval-Period")):
                last_error = msg.content
        break

    return {"chart_files": chart_files, "last_error": last_error}


def build_graph():
    """Build the LangGraph workflow."""
    tool_node = ToolNode(tools)

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_node("track_charts", track_chart_files)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "track_charts")
    builder.add_edge("track_charts", "agent")

    return builder.compile()


graph = build_graph()
