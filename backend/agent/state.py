from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph 에이전트 상태 정의"""
    messages: Annotated[list, add_messages]
    chart_files: list[str]   # 생성된 차트 파일명 목록
    last_error: str          # 마지막 에러 메시지