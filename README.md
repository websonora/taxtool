# Tax Document Backup Portal MVP

Local internal web app for tax-office PDF backup workflow.

## MVP workflow

1. Choose the income tax season. The selected season controls both the prior backup folder and final output folder.
2. Search/select last year's client PDF from a server-mounted shared folder, or upload a demo PDF manually.
3. View page thumbnails in browser.
4. Mark old pages to delete; unmarked pages carry forward.
5. Upload current-season PDFs such as W-2s and 1099s.
6. Create merged backup PDF in the selected season folder.

Example: choosing the `2025` season searches the `2024` backup folder and saves the final PDF into the `2025` folder. Choosing the `2026` season searches `2025` and saves into `2026`.

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
- `/api/health` reports whether the configured shared folder is present.
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
