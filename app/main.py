import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.pdf_service import (
    create_pdf_from_selected_pages,
    get_page_count,
    merge_pdfs,
    render_page_thumbnail,
)
from app.storage import append_audit_log, resolve_output_path, sanitize_filename

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("TAX_PORTAL_DATA_DIR", PROJECT_ROOT / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"
TEMP_DIR = DATA_DIR / "temp"

UPLOADED_PRIOR_PDFS: dict[str, Path] = {}

app = FastAPI(title="Tax Document Backup Portal")
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app" / "static"), name="static")


def _ensure_dirs() -> None:
    for directory in (UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def _require_pdf(upload: UploadFile) -> None:
    filename = upload.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")


def _parse_selected_pages(selected_pages: str) -> list[int]:
    try:
        pages = [int(item.strip()) for item in selected_pages.split(",") if item.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Selected pages must be comma-separated numbers") from exc
    if not pages:
        raise HTTPException(status_code=400, detail="Select at least one page to keep")
    return pages


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    index_path = PROJECT_ROOT / "app" / "templates" / "index.html"
    return index_path.read_text(encoding="utf-8")


@app.post("/api/prior-pdf")
def upload_prior_pdf(file: Annotated[UploadFile, File(...)]) -> dict:
    _require_pdf(file)
    _ensure_dirs()

    document_id = uuid.uuid4().hex
    clean_filename = sanitize_filename(file.filename or "prior.pdf")
    destination = UPLOAD_DIR / f"{document_id}-{clean_filename}"

    with destination.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    UPLOADED_PRIOR_PDFS[document_id] = destination
    return {
        "document_id": document_id,
        "filename": clean_filename,
        "page_count": get_page_count(destination),
    }


@app.get("/api/prior-pdf/{document_id}/thumbnail/{page_number}")
def thumbnail(document_id: str, page_number: int) -> Response:
    source = UPLOADED_PRIOR_PDFS.get(document_id)
    if source is None or not source.exists():
        raise HTTPException(status_code=404, detail="Prior PDF not found")

    try:
        data = render_page_thumbnail(source, page_number, zoom=0.75)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=data, media_type="image/png")


@app.post("/api/create-backup")
def create_backup(
    document_id: Annotated[str, Form(...)],
    selected_pages: Annotated[str, Form(...)],
    tax_year: Annotated[str, Form(...)],
    client_filename: Annotated[str, Form(...)],
    current_year_files: list[UploadFile] | None = File(default=None),
) -> dict:
    source = UPLOADED_PRIOR_PDFS.get(document_id)
    if source is None or not source.exists():
        raise HTTPException(status_code=404, detail="Prior PDF not found")

    _ensure_dirs()
    pages = _parse_selected_pages(selected_pages)
    work_id = uuid.uuid4().hex
    selected_pdf = TEMP_DIR / f"{work_id}-selected.pdf"
    create_pdf_from_selected_pages(source, pages, selected_pdf)

    merge_inputs: list[Path] = [selected_pdf]
    saved_current_year_files: list[str] = []
    for upload in current_year_files or []:
        if upload.filename:
            _require_pdf(upload)
            clean_name = sanitize_filename(upload.filename)
            destination = TEMP_DIR / f"{work_id}-{clean_name}"
            with destination.open("wb") as handle:
                shutil.copyfileobj(upload.file, handle)
            merge_inputs.append(destination)
            saved_current_year_files.append(clean_name)

    output_path = resolve_output_path(OUTPUT_DIR, tax_year, client_filename)
    merge_pdfs(merge_inputs, output_path)

    record = {
        "document_id": document_id,
        "prior_pdf": str(source),
        "selected_pages": pages,
        "tax_year": tax_year,
        "client_filename": sanitize_filename(client_filename),
        "current_year_files": saved_current_year_files,
        "output_path": str(output_path),
    }
    append_audit_log(OUTPUT_DIR, record)

    return {
        "ok": True,
        "output_path": str(output_path),
        "audit": record,
    }
