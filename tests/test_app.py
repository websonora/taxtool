from pathlib import Path

import fitz
from fastapi.testclient import TestClient

import app.main as main
from app.pdf_service import get_page_count


def make_pdf(path: Path, labels: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for label in labels:
        page = doc.new_page(width=200, height=200)
        page.insert_text((72, 100), label)
    doc.save(path)
    doc.close()
    return path


def configure_tmp_data(monkeypatch, tmp_path, with_document_root: bool = False):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "UPLOAD_DIR", data_dir / "uploads")
    monkeypatch.setattr(main, "OUTPUT_DIR", data_dir / "output")
    monkeypatch.setattr(main, "TEMP_DIR", data_dir / "temp")
    if with_document_root:
        monkeypatch.setattr(main, "DOCUMENT_ROOT", tmp_path / "tax-documents")
    else:
        monkeypatch.setattr(main, "DOCUMENT_ROOT", None)
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


def test_search_prior_pdfs_lists_matching_files_from_document_root(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path, with_document_root=True)
    make_pdf(main.DOCUMENT_ROOT / "2024" / "Juan Garcia.pdf", ["old id"])
    make_pdf(main.DOCUMENT_ROOT / "2024" / "Maria Lopez.pdf", ["old id"])
    client = TestClient(main.app)

    response = client.get("/api/shared/prior-pdfs", params={"year": "2024", "query": "juan"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_root"] == str(main.DOCUMENT_ROOT)
    assert payload["results"] == [
        {"filename": "Juan Garcia.pdf", "relative_path": "2024/Juan Garcia.pdf", "year": "2024"}
    ]


def test_open_prior_pdf_from_document_root_registers_document(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path, with_document_root=True)
    make_pdf(main.DOCUMENT_ROOT / "2024" / "Juan Garcia.pdf", ["old id", "old w2"])
    client = TestClient(main.app)

    response = client.post("/api/shared/prior-pdf", data={"relative_path": "2024/Juan Garcia.pdf"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "Juan Garcia.pdf"
    assert payload["page_count"] == 2
    assert main.UPLOADED_PRIOR_PDFS[payload["document_id"]] == main.DOCUMENT_ROOT / "2024" / "Juan Garcia.pdf"


def test_open_prior_pdf_from_document_root_rejects_traversal(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path, with_document_root=True)
    client = TestClient(main.app)

    response = client.post("/api/shared/prior-pdf", data={"relative_path": "../secret.pdf"})

    assert response.status_code == 400


def test_create_backup_with_document_root_saves_into_tax_year_folder(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path, with_document_root=True)
    make_pdf(main.DOCUMENT_ROOT / "2024" / "Juan Garcia.pdf", ["old id", "old w2"])
    new_doc = make_pdf(tmp_path / "new.pdf", ["new 2025 w2"])
    client = TestClient(main.app)

    open_response = client.post("/api/shared/prior-pdf", data={"relative_path": "2024/Juan Garcia.pdf"})
    document_id = open_response.json()["document_id"]

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
    output_path = Path(response.json()["output_path"])
    assert output_path == main.DOCUMENT_ROOT / "2025" / "Juan Garcia.pdf"
    assert output_path.exists()
    assert get_page_count(output_path) == 2
    assert (main.DOCUMENT_ROOT / "audit.jsonl").exists()


def test_search_current_pdfs_lists_current_scans_documents(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path, with_document_root=True)
    make_pdf(main.DOCUMENT_ROOT / "CienteActual" / "Juan W2.pdf", ["new w2"])
    make_pdf(main.DOCUMENT_ROOT / "CienteActual" / "Maria 1099.pdf", ["new 1099"])
    client = TestClient(main.app)

    response = client.get("/api/shared/current-pdfs", params={"year": "2025", "query": "juan"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_scans_folder"] == str(main.DOCUMENT_ROOT / "CienteActual")
    assert payload["results"] == [
        {"filename": "Juan W2.pdf", "relative_path": "CienteActual/Juan W2.pdf", "year": "2025"}
    ]


def test_create_backup_can_merge_selected_current_scans_files(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path, with_document_root=True)
    make_pdf(main.DOCUMENT_ROOT / "2024" / "Juan Garcia.pdf", ["old id", "old w2"])
    make_pdf(main.DOCUMENT_ROOT / "CienteActual" / "Juan W2.pdf", ["new w2"])
    make_pdf(main.DOCUMENT_ROOT / "CienteActual" / "Juan 1099.pdf", ["new 1099"])
    client = TestClient(main.app)

    open_response = client.post("/api/shared/prior-pdf", data={"relative_path": "2024/Juan Garcia.pdf"})
    document_id = open_response.json()["document_id"]

    response = client.post(
        "/api/create-backup",
        data={
            "document_id": document_id,
            "selected_pages": "1",
            "tax_year": "2025",
            "client_filename": "Juan Garcia.pdf",
            "current_shared_paths": ["CienteActual/Juan W2.pdf", "CienteActual/Juan 1099.pdf"],
        },
    )

    assert response.status_code == 200
    output_path = Path(response.json()["output_path"])
    assert output_path == main.DOCUMENT_ROOT / "2025" / "Juan Garcia.pdf"
    assert get_page_count(output_path) == 3


def test_create_backup_returns_download_url_and_download_endpoint_serves_pdf(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path)
    prior = make_pdf(tmp_path / "prior.pdf", ["old id"])
    client = TestClient(main.app)

    with prior.open("rb") as handle:
        upload = client.post("/api/prior-pdf", files={"file": ("prior.pdf", handle, "application/pdf")})
    document_id = upload.json()["document_id"]

    response = client.post(
        "/api/create-backup",
        data={
            "document_id": document_id,
            "selected_pages": "1",
            "tax_year": "2025",
            "client_filename": "Juan Garcia.pdf",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["output_id"]
    assert payload["download_url"] == f"/api/output/{payload['output_id']}/download"

    download = client.get(payload["download_url"])

    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF")


def test_download_endpoint_rejects_unknown_output_id(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = client.get("/api/output/not-real/download")

    assert response.status_code == 404


def test_health_reports_shared_folder_status(monkeypatch, tmp_path):
    configure_tmp_data(monkeypatch, tmp_path, with_document_root=True)
    main.DOCUMENT_ROOT.mkdir(parents=True)
    client = TestClient(main.app)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["document_root_configured"] is True
    assert payload["document_root_exists"] is True
    assert payload["output_base"] == str(main.DOCUMENT_ROOT)


def test_root_ui_includes_page_preview_modal_and_delete_workflow_copy():
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "previewModal" in response.text
    assert "Preview pages before deciding what to delete" in response.text
    assert "Marked Delete" in response.text


def test_root_ui_includes_income_tax_season_selector():
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "incomeTaxSeason" in response.text
    assert "2022 season" in response.text
    assert "2023 season" in response.text
    assert "2024 season" in response.text
    assert "2025 season" in response.text
    assert "2026 season" in response.text
    assert "Backup folder to search" in response.text
    assert "Final document save folder" in response.text


def test_root_ui_includes_current_scans_and_continue_controls():
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "CienteActual" in response.text
    assert "Search CienteActual" in response.text
    assert "confirmAndContinue" in response.text
    assert "Everything went OK" in response.text


def test_frontend_script_builds_preview_and_delete_controls():
    script = (main.PROJECT_ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "pagesToDelete" in script
    assert "Preview" in script
    assert "Mark Delete" in script
    assert "openPreview" in script


def test_frontend_script_syncs_income_tax_season_to_backup_and_output_years():
    script = (main.PROJECT_ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "incomeTaxSeason" in script
    assert "backupYearForSeason" in script
    assert "Number.parseInt(season, 10) - 1" in script
    assert "resetBackupFolder" in script
    assert "sharedYear.value = defaultBackupYear" in script
    assert "taxYear.value = season" in script
    assert "clearActiveDocument" in script
    assert "selectedCurrentPdfs" in script
