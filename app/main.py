import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
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
document_root_env = os.getenv("TAX_PORTAL_DOCUMENT_ROOT")
DEFAULT_WINDOWS_DOCUMENT_ROOT = Path(r"T:\INCOME TAX REPORTS")
DOCUMENT_ROOT = Path(document_root_env) if document_root_env else DEFAULT_WINDOWS_DOCUMENT_ROOT if os.name == "nt" else None
CURRENT_SCANS_FOLDER_NAMES = ("ClienteActual", "CienteActual")

UPLOADED_PRIOR_PDFS: dict[str, Path] = {}
CREATED_OUTPUTS: dict[str, Path] = {}

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


def _require_document_root() -> Path:
    if DOCUMENT_ROOT is None:
        raise HTTPException(status_code=400, detail="Shared document root is not configured")
    return DOCUMENT_ROOT


def _safe_shared_pdf_path(relative_path: str) -> Path:
    root = _require_document_root().resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid shared PDF path") from exc
    if candidate.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Shared PDF not found")
    return candidate


def _pdf_result(path: Path, root: Path, year: str) -> dict:
    return {
        "filename": path.name,
        "relative_path": path.relative_to(root).as_posix(),
        "year": year,
    }


def _search_pdfs(folder: Path, root: Path, year: str, query: str) -> list[dict]:
    if not folder.exists():
        return []

    needle = query.casefold().strip()
    results = []
    for path in sorted(folder.rglob("*.pdf")):
        if needle and needle not in path.name.casefold():
            continue
        results.append(_pdf_result(path, root, year))
        if len(results) >= 50:
            break
    return results


def _current_scans_dir(root: Path, tax_year: str) -> Path:
    for folder_name in CURRENT_SCANS_FOLDER_NAMES:
        root_level_scans = root / folder_name
        if root_level_scans.exists():
            return root_level_scans
    return root / tax_year / CURRENT_SCANS_FOLDER_NAMES[0]


def _safe_current_pdf_path(relative_path: str, tax_year: str) -> Path:
    source = _safe_shared_pdf_path(relative_path)
    root = _require_document_root().resolve()
    current_scans = _current_scans_dir(root, tax_year).resolve()
    try:
        source.resolve().relative_to(current_scans)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Current document must be inside ClienteActual/CienteActual") from exc
    return source


def _output_base_dir() -> Path:
    return DOCUMENT_ROOT if DOCUMENT_ROOT is not None else OUTPUT_DIR


def _output_id() -> str:
    return uuid.uuid4().hex


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    index_path = PROJECT_ROOT / "app" / "templates" / "index.html"
    return index_path.read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    output_base = _output_base_dir()
    document_root_exists = DOCUMENT_ROOT.exists() if DOCUMENT_ROOT is not None else False
    output_base_exists = output_base.exists()
    return {
        "ok": DOCUMENT_ROOT is None or document_root_exists,
        "document_root_configured": DOCUMENT_ROOT is not None,
        "document_root": str(DOCUMENT_ROOT) if DOCUMENT_ROOT is not None else None,
        "document_root_exists": document_root_exists,
        "output_base": str(output_base),
        "output_base_exists": output_base_exists,
    }


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


@app.get("/api/shared/prior-pdfs")
def search_shared_prior_pdfs(
    year: Annotated[str, Query(min_length=4, max_length=4)],
    query: str = "",
) -> dict:
    root = _require_document_root()
    year_dir = root / year
    return {"document_root": str(root), "results": _search_pdfs(year_dir, root, year, query)}


@app.get("/api/shared/current-pdfs")
def search_shared_current_pdfs(
    year: Annotated[str, Query(min_length=4, max_length=4)],
    query: str = "",
) -> dict:
    root = _require_document_root()
    current_scans = _current_scans_dir(root, year)
    return {
        "document_root": str(root),
        "current_scans_folder": str(current_scans),
        "cliente_actual_folder": str(current_scans),
        "results": _search_pdfs(current_scans, root, year, query),
    }


@app.post("/api/shared/prior-pdf")
def open_shared_prior_pdf(relative_path: Annotated[str, Form(...)]) -> dict:
    source = _safe_shared_pdf_path(relative_path)
    document_id = uuid.uuid4().hex
    UPLOADED_PRIOR_PDFS[document_id] = source
    return {
        "document_id": document_id,
        "filename": source.name,
        "page_count": get_page_count(source),
        "relative_path": source.relative_to(_require_document_root()).as_posix(),
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
    current_shared_paths: list[str] | None = Form(default=None),
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
    for relative_path in current_shared_paths or []:
        shared_source = _safe_current_pdf_path(relative_path, tax_year)
        merge_inputs.append(shared_source)
        saved_current_year_files.append(shared_source.relative_to(_require_document_root()).as_posix())

    for upload in current_year_files or []:
        if upload.filename:
            _require_pdf(upload)
            clean_name = sanitize_filename(upload.filename)
            destination = TEMP_DIR / f"{work_id}-{clean_name}"
            with destination.open("wb") as handle:
                shutil.copyfileobj(upload.file, handle)
            merge_inputs.append(destination)
            saved_current_year_files.append(clean_name)

    output_base = _output_base_dir()
    output_path = resolve_output_path(output_base, tax_year, client_filename)
    merge_pdfs(merge_inputs, output_path)
    output_id = _output_id()
    CREATED_OUTPUTS[output_id] = output_path

    record = {
        "document_id": document_id,
        "prior_pdf": str(source),
        "selected_pages": pages,
        "tax_year": tax_year,
        "client_filename": sanitize_filename(client_filename),
        "current_year_files": saved_current_year_files,
        "output_path": str(output_path),
    }
    append_audit_log(output_base, record)

    return {
        "ok": True,
        "output_id": output_id,
        "output_path": str(output_path),
        "download_url": f"/api/output/{output_id}/download",
        "audit": record,
    }


@app.get("/api/output/{output_id}/download")
def download_output(output_id: str) -> FileResponse:
    output_path = CREATED_OUTPUTS.get(output_id)
    if output_path is None or not output_path.exists():
        raise HTTPException(status_code=404, detail="Output PDF not found")
    return FileResponse(output_path, media_type="application/pdf", filename=output_path.name)
