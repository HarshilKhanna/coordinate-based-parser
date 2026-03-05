"""
FastAPI application — Cause List PDF Parser

Pipeline:
  PDF bytes → coordinate extraction → row grouping → column zoning
  → state machine parser → regex case numbers → JSON response
"""

import logging

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .parser import CauseListParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cause List Parser",
    description="Parse Indian court cause list PDFs into structured JSON",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Cause List Parser API", "version": "3.0.0"}


@app.post("/upload")
async def parse_cause_list(file: UploadFile = File(...)):
    """Upload a cause list PDF and receive structured JSON."""
    logger.info("Received file: %s", file.filename)

    pdf_bytes = await file.read()

    parser = CauseListParser(
        court_name="Madras High Court",
    )
    records = parser.parse_bytes(pdf_bytes, skip_pages=5)
    summary = parser.summary()

    logger.info(
        "Complete: %d items | regex=%d (%.0f%%) | partial=%d | llm_needed=%d",
        summary["total_items"],
        summary["regex_success"],
        summary["regex_pct"],
        summary["partial"],
        summary["llm_needed"],
    )

    return records


@app.post("/debug")
async def debug_pdf(file: UploadFile = File(...)):
    """Debug endpoint: show parser state and sample records."""
    pdf_bytes = await file.read()

    parser = CauseListParser(court_name="Madras High Court")
    records = parser.parse_bytes(pdf_bytes, skip_pages=5)
    summary = parser.summary()

    return {
        "summary": summary,
        "total_records": len(records),
        "sample_records": records[:20],
    }
