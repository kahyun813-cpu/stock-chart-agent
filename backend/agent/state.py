from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State passed between LangGraph nodes."""

    messages: Annotated[list, add_messages]
    chart_files: list[str]
    last_error: str
