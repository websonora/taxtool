from pathlib import Path

import fitz
from fastapi.testclient import TestClient

import app.main as main
from app.pdf_service import get_page_count


def make_pdf(path: Path, labels: list[str]) -> Path:
    doc = fitz.open()
    for label in labels:
        page = doc.new_page(width=200, height=200)
        page.insert_text((72, 100), label)
    doc.save(path)
    doc.close()
    return path


def configure_tmp_data(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "UPLOAD_DIR", data_dir / "uploads")
    monkeypatch.setattr(main, "OUTPUT_DIR", data_dir / "output")
    monkeypatch.setattr(main, "TEMP_DIR", data_dir / "temp")
    main.UPLOADED_PRIOR_PDFS.clear()


def test_root_returns_portal_ui():
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Tax Document Backup Portal" in response.text


def test_upload_prior_pdf_returns_document_id_and_page_count(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path)
    pdf = make_pdf(tmp_path / "prior.pdf", ["page 1", "page 2"])
    client = TestClient(main.app)

    with pdf.open("rb") as handle:
        response = client.post("/api/prior-pdf", files={"file": ("prior.pdf", handle, "application/pdf")})

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "prior.pdf"
    assert payload["page_count"] == 2
    assert payload["document_id"]


def test_thumbnail_endpoint_returns_png(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path)
    pdf = make_pdf(tmp_path / "prior.pdf", ["page 1"])
    client = TestClient(main.app)

    with pdf.open("rb") as handle:
        upload = client.post("/api/prior-pdf", files={"file": ("prior.pdf", handle, "application/pdf")})
    document_id = upload.json()["document_id"]

    response = client.get(f"/api/prior-pdf/{document_id}/thumbnail/1")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_create_backup_merges_selected_old_pages_with_new_pdfs(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path)
    prior = make_pdf(tmp_path / "prior.pdf", ["old id", "old w2"])
    new_doc = make_pdf(tmp_path / "new.pdf", ["new 2025 w2"])
    client = TestClient(main.app)

    with prior.open("rb") as handle:
        upload = client.post("/api/prior-pdf", files={"file": ("prior.pdf", handle, "application/pdf")})
    document_id = upload.json()["document_id"]

    with new_doc.open("rb") as handle:
        response = client.post(
            "/api/create-backup",
            data={
                "document_id": document_id,
                "selected_pages": "1",
                "tax_year": "2025",
                "client_filename": "Juan Garcia.pdf",
            },
            files=[("current_year_files", ("new.pdf", handle, "application/pdf"))],
        )

    assert response.status_code == 200
    payload = response.json()
    output_path = Path(payload["output_path"])
    assert output_path.exists()
    assert output_path.name == "Juan Garcia.pdf"
    assert get_page_count(output_path) == 2
    assert (main.OUTPUT_DIR / "audit.jsonl").exists()
