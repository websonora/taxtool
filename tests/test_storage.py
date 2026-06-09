import json

from app.storage import append_audit_log, resolve_output_path, sanitize_filename


def test_sanitize_filename_removes_path_and_bad_characters():
    assert sanitize_filename("../Juan:Garcia?.pdf") == "Juan_Garcia_.pdf"


def test_sanitize_filename_adds_pdf_extension():
    assert sanitize_filename("Juan Garcia") == "Juan Garcia.pdf"


def test_resolve_output_path_creates_year_folder_and_returns_clean_pdf_path(tmp_path):
    output = resolve_output_path(tmp_path, "2025", "../Juan:Garcia?.pdf")

    assert output == tmp_path / "2025" / "Juan_Garcia_.pdf"
    assert output.parent.exists()


def test_resolve_output_path_versions_existing_files(tmp_path):
    first = resolve_output_path(tmp_path, "2025", "Juan Garcia.pdf")
    first.write_bytes(b"existing")

    second = resolve_output_path(tmp_path, "2025", "Juan Garcia.pdf")

    assert second.name == "Juan Garcia - version 2.pdf"


def test_append_audit_log_writes_json_line(tmp_path):
    log_path = append_audit_log(tmp_path, {"client": "Juan Garcia", "year": "2025"})

    lines = log_path.read_text().splitlines()
    assert log_path.name == "audit.jsonl"
    assert json.loads(lines[0])["client"] == "Juan Garcia"
