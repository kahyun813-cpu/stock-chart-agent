import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

load_dotenv()

CHARTS_DIR = os.getenv("CHARTS_DIR", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log backend startup and shutdown events."""
    print("Stock Chart Agent backend starting...")
    yield
    print("Stock Chart Agent backend shutting down...")


app = FastAPI(
    title="Stock Chart Agent API",
    description="AI-powered stock chart visualization agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    chart_files: list[str] = []
    error: str = ""


conversation_history: dict[str, list] = {}


@app.get("/")
async def root():
    return {"message": "Stock Chart Agent API is running."}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "charts_dir": CHARTS_DIR}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Run the chart agent, with a local fallback if the LLM is unavailable."""
    try:
        from backend.agent.graph import graph

        history = conversation_history.get(request.session_id, [])
        history.append(HumanMessage(content=request.message))

        result = graph.invoke(
            {
                "messages": history,
                "chart_files": [],
                "last_error": "",
            }
        )

        conversation_history[request.session_id] = result["messages"]

        last_message = result["messages"][-1]
        response_text = last_message.content if hasattr(last_message, "content") else str(last_message)

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
    """Serve a generated HTML chart file."""
    filepath = os.path.join(CHARTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Chart not found: {filename}")
    return FileResponse(filepath, media_type="text/html")


@app.get("/charts")
async def list_charts():
    """List generated chart files."""
    if not os.path.exists(CHARTS_DIR):
        return {"charts": []}
    charts = [filename for filename in os.listdir(CHARTS_DIR) if filename.endswith(".html")]
    return {"charts": sorted(charts, reverse=True)}


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear session chat history."""
    if session_id in conversation_history:
        del conversation_history[session_id]
    return {"message": f"Session {session_id} cleared"}
