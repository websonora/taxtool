# Tax Document Backup Portal MVP

Local internal web app for tax-office PDF backup workflow.

## MVP workflow

1. Search/select prior-year client PDF from a server-mounted shared folder, or upload a demo PDF manually.
2. View page thumbnails in browser.
3. Click pages to carry forward.
4. Upload current-year PDFs such as W-2s and 1099s.
5. Create merged backup PDF in the selected tax year folder.

## File access modes

### Shared-folder mode — production target

The Linux app server mounts the office tax document share, for example:

```text
/mnt/tax-documents/
  2024/
  2025/
```

Start the app with:

```bash
export TAX_PORTAL_DOCUMENT_ROOT=/mnt/tax-documents
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8088
```

When `TAX_PORTAL_DOCUMENT_ROOT` is set:

- `/api/shared/prior-pdfs` searches prior-year PDFs under that root.
- `/api/shared/prior-pdf` opens a selected shared PDF.
- `/api/create-backup` saves final PDFs directly into `<DOCUMENT_ROOT>/<tax_year>/`.
- Audit log is written to `<DOCUMENT_ROOT>/audit.jsonl`.

### Upload demo mode

If no shared folder is configured, users can still upload a prior PDF manually. Output saves under:

```text
data/output/<tax_year>/
```

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e . pytest httpx
python3 -m pytest tests -q
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8088
```

LAN URL on Hermes VM: `http://192.168.1.232:8088`
