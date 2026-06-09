from pathlib import Path

import fitz
import pytest

from app.pdf_service import (
    create_pdf_from_selected_pages,
    get_page_count,
    merge_pdfs,
    render_page_thumbnail,
)


def make_pdf(path: Path, labels: list[str]) -> Path:
    doc = fitz.open()
    for label in labels:
        page = doc.new_page(width=200, height=200)
        page.insert_text((72, 100), label)
    doc.save(path)
    doc.close()
    return path


def extract_texts(path: Path) -> list[str]:
    doc = fitz.open(path)
    try:
        return [page.get_text() for page in doc]
    finally:
        doc.close()


def test_get_page_count_returns_number_of_pages(tmp_path):
    pdf = make_pdf(tmp_path / "client.pdf", ["page 1", "page 2", "page 3"])

    assert get_page_count(pdf) == 3


def test_render_page_thumbnail_returns_png_bytes(tmp_path):
    pdf = make_pdf(tmp_path / "client.pdf", ["page 1"])

    data = render_page_thumbnail(pdf, 1)

    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_create_pdf_from_selected_pages_uses_one_based_page_numbers(tmp_path):
    source = make_pdf(tmp_path / "source.pdf", ["keep 1", "skip", "keep 3"])
    output = tmp_path / "selected.pdf"

    create_pdf_from_selected_pages(source, [1, 3], output)

    assert get_page_count(output) == 2
    texts = extract_texts(output)
    assert "keep 1" in texts[0]
    assert "keep 3" in texts[1]


def test_create_pdf_from_selected_pages_rejects_invalid_page_numbers(tmp_path):
    source = make_pdf(tmp_path / "source.pdf", ["only page"])

    with pytest.raises(ValueError):
        create_pdf_from_selected_pages(source, [0], tmp_path / "bad.pdf")

    with pytest.raises(ValueError):
        create_pdf_from_selected_pages(source, [2], tmp_path / "bad.pdf")


def test_merge_pdfs_preserves_input_order(tmp_path):
    first = make_pdf(tmp_path / "first.pdf", ["old id"] )
    second = make_pdf(tmp_path / "second.pdf", ["new w2", "new 1099"] )
    output = tmp_path / "merged.pdf"

    merge_pdfs([first, second], output)

    assert get_page_count(output) == 3
    texts = extract_texts(output)
    assert "old id" in texts[0]
    assert "new w2" in texts[1]
    assert "new 1099" in texts[2]
