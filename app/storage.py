import json
import re
from datetime import datetime, timezone
from pathlib import Path

_BAD_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
_YEAR_PATTERN = re.compile(r"^\d{4}$")


def sanitize_filename(name: str) -> str:
    candidate = Path(name).name.strip()
    candidate = _BAD_FILENAME_CHARS.sub("_", candidate)
    candidate = candidate.strip(" .")
    if not candidate:
        candidate = "document"
    if not candidate.lower().endswith(".pdf"):
        candidate = f"{candidate}.pdf"
    return candidate


def resolve_output_path(base_dir: str | Path, year: str, client_filename: str) -> Path:
    if not _YEAR_PATTERN.match(str(year)):
        raise ValueError("Tax year must be a 4-digit year")

    year_dir = Path(base_dir) / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    clean_name = sanitize_filename(client_filename)
    candidate = year_dir / clean_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    version = 2
    while True:
        versioned = year_dir / f"{stem} - version {version}{suffix}"
        if not versioned.exists():
            return versioned
        version += 1


def append_audit_log(base_dir: str | Path, record: dict) -> Path:
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)
    log_path = base_path / "audit.jsonl"
    enriched = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(enriched, sort_keys=True) + "\n")
    return log_path
