"""
FastAPI application — Cause List PDF Parser

Pipeline:
  PDF bytes → coordinate extraction → row grouping → column zoning
  → state machine parser → regex case numbers → JSON response

Upload returns immediately with a task_id.
Use GET /status/{task_id} to poll for results.
"""

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from parser import CauseListParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cause List Parser",
    description="Parse Indian court cause list PDFs into structured JSON",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task store  {task_id: {"status": ..., "result": ..., "error": ...}}
tasks: dict = {}
_executor = ThreadPoolExecutor()


# ── sync worker (runs in thread pool so it doesn't block the event loop) ──────
def _parse_sync(task_id: str, pdf_bytes: bytes) -> None:
    try:
        tasks[task_id]["status"] = "processing"
        logger.info("Task %s: starting parse (%d bytes)", task_id, len(pdf_bytes))

        parser = CauseListParser(court_name="Madras High Court")
        records = parser.parse_bytes(pdf_bytes, skip_pages=5, max_pages=25)
        summary = parser.summary()

        logger.info(
            "Task %s complete: %d items | regex=%d (%.0f%%) | partial=%d | llm_needed=%d",
            task_id,
            summary["total_items"],
            summary["regex_success"],
            summary["regex_pct"],
            summary["partial"],
            summary["llm_needed"],
        )

        tasks[task_id] = {"status": "done", "result": records, "summary": summary}
    except Exception as exc:
        logger.exception("Task %s failed: %s", task_id, exc)
        tasks[task_id] = {"status": "error", "error": str(exc)}


async def _parse_background(task_id: str, pdf_bytes: bytes) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _parse_sync, task_id, pdf_bytes)


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Cause List Parser API", "version": "4.0.0"}


@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Accept a cause list PDF, queue the parse job, and return a task_id
    immediately.  The heavy work runs in the background so Render's
    30-second request timeout is never hit.
    """
    pdf_bytes = await file.read()
    task_id = str(uuid.uuid4())

    tasks[task_id] = {"status": "queued"}
    background_tasks.add_task(_parse_background, task_id, pdf_bytes)

    logger.info("Task %s queued for file: %s", task_id, file.filename)
    return {"task_id": task_id}


@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Poll this endpoint with the task_id returned by /upload.

    Response shapes:
      {"status": "queued"}
      {"status": "processing"}
      {"status": "done",  "result": [...], "summary": {...}}
      {"status": "error", "error": "...message..."}
      {"status": "not_found"}
    """
    return tasks.get(task_id, {"status": "not_found"})


@app.post("/debug")
async def debug_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Debug endpoint: queues parse and returns task_id (same async pattern)."""
    pdf_bytes = await file.read()
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "queued"}
    background_tasks.add_task(_parse_background, task_id, pdf_bytes)
    return {"task_id": task_id, "note": "poll /status/{task_id} for results"}
