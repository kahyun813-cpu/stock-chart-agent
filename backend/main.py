import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

# 차트 저장 폴더 생성
CHARTS_DIR = os.getenv("CHARTS_DIR", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 이벤트"""
    print("🚀 Stock Chart Agent Backend Starting...")
    yield
    print("👋 Backend Shutting Down...")


app = FastAPI(
    title="Stock Chart Agent API",
    description="AI-powered stock chart visualization agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정 (Streamlit → FastAPI 통신 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 요청/응답 모델 ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    chart_files: list[str] = []
    error: str = ""


# ── 세션별 대화 기록 (메모리) ──────────────────────────────────────
conversation_history: dict[str, list] = {}


# ── 엔드포인트 ─────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Stock Chart Agent API is running! 📈"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "charts_dir": CHARTS_DIR}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """에이전트와 채팅"""
    try:
        # 지연 임포트 (앱 시작 속도 최적화)
        from backend.agent.graph import graph

        # 세션 기록 가져오기 (없으면 새로 만들기)
        history = conversation_history.get(request.session_id, [])
        history.append(HumanMessage(content=request.message))

        # 에이전트 실행
        result = graph.invoke(
            {
                "messages": history,
                "chart_files": [],
                "last_error": "",
            }
        )

        # 대화 기록 업데이트
        conversation_history[request.session_id] = result["messages"]

        # 마지막 AI 응답 추출
        last_message = result["messages"][-1]
        response_text = last_message.content if hasattr(last_message, "content") else str(last_message)

        # CHART_FILE 태그 제거 (UI에 노출 방지)
        if "CHART_FILE:" in response_text:
            response_text = response_text.split("CHART_FILE:")[0].strip()

        return ChatResponse(
            response=response_text,
            chart_files=result.get("chart_files", []),
            error=result.get("last_error", ""),
        )

    except Exception as e:
        try:
            from backend.agent.fallback import run_local_chart_fallback

            fallback_result = run_local_chart_fallback(request.message)
            return ChatResponse(
                response=fallback_result["response"],
                chart_files=fallback_result.get("chart_files", []),
                error=fallback_result.get("error", ""),
            )
        except Exception as fallback_error:
            raise HTTPException(
                status_code=500,
                detail=f"Agent error: {str(e)}; fallback error: {str(fallback_error)}",
            )


@app.get("/charts/{filename}")
async def get_chart(filename: str):
    """HTML 차트 파일 제공"""
    filepath = os.path.join(CHARTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Chart not found: {filename}")
    return FileResponse(filepath, media_type="text/html")


@app.get("/charts")
async def list_charts():
    """생성된 모든 차트 목록"""
    if not os.path.exists(CHARTS_DIR):
        return {"charts": []}
    charts = [f for f in os.listdir(CHARTS_DIR) if f.endswith(".html")]
    return {"charts": sorted(charts, reverse=True)}


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """세션 대화 기록 초기화"""
    if session_id in conversation_history:
        del conversation_history[session_id]
    return {"message": f"Session {session_id} cleared"}
