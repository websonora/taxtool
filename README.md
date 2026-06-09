# Tax Document Backup Portal MVP

Local internal web app for tax-office PDF backup workflow.

## MVP workflow

1. Upload/select prior-year client PDF.
2. View page thumbnails in browser.
3. Click pages to carry forward.
4. Upload current-year PDFs such as W-2s and 1099s.
5. Create merged backup PDF in the selected tax year folder.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e . pytest httpx
python3 -m pytest tests -q
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8088
```

LAN URL on Hermes VM: `http://192.168.1.232:8088`
