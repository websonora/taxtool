from pathlib import Path

import fitz


def _as_path(path: str | Path) -> Path:
    return Path(path)


def _validate_page_number(page_number: int, page_count: int) -> None:
    if page_number < 1 or page_number > page_count:
        raise ValueError(f"Page number {page_number} is outside valid range 1-{page_count}")


def get_page_count(path: str | Path) -> int:
    doc = fitz.open(_as_path(path))
    try:
        return doc.page_count
    finally:
        doc.close()


def render_page_thumbnail(path: str | Path, page_number: int, zoom: float = 0.25) -> bytes:
    doc = fitz.open(_as_path(path))
    try:
        _validate_page_number(page_number, doc.page_count)
        page = doc.load_page(page_number - 1)
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")
    finally:
        doc.close()


def create_pdf_from_selected_pages(source_path: str | Path, selected_pages: list[int], output_path: str | Path) -> Path:
    if not selected_pages:
        raise ValueError("At least one page must be selected")

    source = fitz.open(_as_path(source_path))
    output = fitz.open()
    output_path = _as_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        for page_number in selected_pages:
            _validate_page_number(page_number, source.page_count)
            zero_based = page_number - 1
            output.insert_pdf(source, from_page=zero_based, to_page=zero_based)
        output.save(output_path)
        return output_path
    finally:
        output.close()
        source.close()


def merge_pdfs(input_paths: list[str | Path], output_path: str | Path) -> Path:
    if not input_paths:
        raise ValueError("At least one PDF is required for merge")

    output = fitz.open()
    output_path = _as_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        for input_path in input_paths:
            src = fitz.open(_as_path(input_path))
            try:
                output.insert_pdf(src)
            finally:
                src.close()
        output.save(output_path)
        return output_path
    finally:
        output.close()
