import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import time
import shutil
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

from app.multimodal.report_analyzer import analyze_report
from app.multimodal.image_processor import analyze_image
from app.multimodal.ocr import process_prescription
from app.agents.graph import build_graph
from app.rag.retriever import load_vector_store, retrieve_with_scores
from app.ingestion.ingest import (
    load_documents,
    chunk_documents,
    build_vector_store,
    RAW_DOCS_PATH,
)
from app.analytics import log_activity, get_stats, estimate_tokens

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="MediAssist AI Backend")

agent_graph = build_graph()

_vector_store_cache = None


def get_cached_vector_store():
    global _vector_store_cache
    if _vector_store_cache is None:
        _vector_store_cache = load_vector_store()
    return _vector_store_cache


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    evaluation: dict | None = None


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 4


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"status": "MediAssist AI backend is running"}


@app.get("/db-health")
def db_health():
    """Actually pings Postgres — previously this route didn't exist at all,
    which is why the frontend always showed 'Database not reachable' (it
    was getting a 404, not a real connection error)."""
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not set")
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
def stats():
    """Dashboard endpoint — aggregated activity stats for the frontend."""
    return get_stats()


@app.post("/upload")
def upload_document(file: UploadFile = File(...)):
    start = time.time()
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    os.makedirs(RAW_DOCS_PATH, exist_ok=True)
    destination = os.path.join(RAW_DOCS_PATH, file.filename)

    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    documents = load_documents()
    chunks = chunk_documents(documents)
    build_vector_store(chunks)

    global _vector_store_cache
    _vector_store_cache = None

    log_activity(
        "upload",
        detail={"filename": file.filename, "chunk_count": len(chunks)},
        response_time=round(time.time() - start, 2),
    )

    return {"status": "uploaded and indexed", "filename": file.filename}


@app.post("/retrieve")
def retrieve_chunks(request: RetrieveRequest):
    vector_store = get_cached_vector_store()
    chunks = retrieve_with_scores(vector_store, request.query, top_k=request.top_k)
    return {"query": request.query, "results": chunks}


@app.post("/analyze-image")
async def analyze_uploaded_image(file: UploadFile = File(...)):
    start = time.time()
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG and JPEG images are supported")

    image_bytes = await file.read()
    result = analyze_image(image_bytes, mime_type=file.content_type)

    log_activity(
        "analyze_image",
        detail={"filename": file.filename},
        response_time=round(time.time() - start, 2),
        tokens_estimate=estimate_tokens(str(result)),
    )

    return {"filename": file.filename, "analysis": result}


@app.post("/read-prescription")
async def read_prescription(file: UploadFile = File(...)):
    start = time.time()
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG and JPEG images are supported")

    image_bytes = await file.read()
    result = process_prescription(image_bytes)

    log_activity(
        "read_prescription",
        detail={"filename": file.filename, "medicines_found": len(result.get("medicines", []))},
        response_time=round(time.time() - start, 2),
        tokens_estimate=estimate_tokens(str(result)),
    )

    return {"filename": file.filename, **result}


@app.post("/analyze-report")
async def analyze_lab_report(file: UploadFile = File(...), use_ocr: bool = True):
    start = time.time()
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG and JPEG images are supported")

    image_bytes = await file.read()
    result = analyze_report(image_bytes, mime_type=file.content_type, use_ocr=use_ocr)

    log_activity(
        "analyze_report",
        detail={"filename": file.filename},
        response_time=round(time.time() - start, 2),
        tokens_estimate=estimate_tokens(str(result)),
    )

    return {"filename": file.filename, **result}


@app.post("/chat", response_model=ChatResponse)
async def chat(query: str = Form(...), image: UploadFile = File(None)):
    start = time.time()
    image_bytes = None
    image_mime_type = None
    if image is not None:
        image_bytes = await image.read()
        image_mime_type = image.content_type

    initial_state = {
        "user_query": query,
        "needs_retrieval": False,
        "needs_mcp": False,
        "needs_vision": False,
        "needs_ocr": False,
        "needs_report_analysis": False,
        "rag_context": None,
        "rag_sources": None,
        "mcp_data": None,
        "vision_data": None,
        "ocr_data": None,
        "report_analysis_data": None,
        "image_bytes": image_bytes,
        "image_mime_type": image_mime_type,
        "final_answer": None,
        "evaluation": None,
    }

    error_occurred = False
    try:
        result = agent_graph.invoke(initial_state)
        answer_text = result.get("final_answer") or "No answer generated."
    except Exception as e:
        error_occurred = True
        answer_text = f"An error occurred while processing this request: {e}"
        result = {}

    decline_phrases = [
        "i'm sorry", "i can't help", "does not contain information",
        "don't have access", "cannot provide",
    ]
    is_decline = any(phrase in answer_text.lower() for phrase in decline_phrases)

    sources = [] if is_decline else (result.get("rag_sources") or [])
    mcp_source = result.get("mcp_source")
    if mcp_source and not is_decline:
        sources = sources + [mcp_source]

    # Determine which agent path actually answered, for dashboard breakdown
    if error_occurred:
        agent_path = "error"
    elif mcp_source:
        agent_path = "mcp"
    elif result.get("vision_data"):
        agent_path = "vision"
    elif result.get("ocr_data"):
        agent_path = "ocr"
    elif result.get("report_analysis_data"):
        agent_path = "report_analysis"
    elif result.get("rag_sources"):
        agent_path = "retriever"
    else:
        agent_path = "reasoning_only"

    response_time = round(time.time() - start, 2)
    tokens_estimate = estimate_tokens(query) + estimate_tokens(answer_text)

    log_activity(
        "chat",
        detail={
            "query": query[:200],
            "agent_path": agent_path,
            "had_image": image is not None,
            "error": error_occurred,
        },
        response_time=response_time,
        tokens_estimate=tokens_estimate,
    )

    return ChatResponse(
        answer=answer_text,
        sources=sources,
        evaluation=result.get("evaluation"),
    )