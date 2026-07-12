# Windows Test Setup Guide — Tax Document Backup Portal

This guide documents the exact Windows test setup steps followed for the Tax Document Backup Portal MVP.

## Purpose

Run the PDF app locally on a Windows test machine so the office can verify:

- Python installation
- App startup
- Local folder access
- PDF preview
- Mark Delete page workflow
- Merge/save behavior

For first tests, use a safe test folder. Do **not** point the app to the real income tax reports folder until the test workflow is verified.

---

## 1. Install Python

Install Python from:

```text
https://www.python.org/downloads/windows/
```

During install, enable one of these options if shown:

```text
Add python.exe to PATH
```

or, on the installer advanced/options screen:

```text
Add Python to environment variables
```

After installation, open PowerShell and test:

```powershell
py --version
```

In our test, Python worked through the Windows Python launcher:

```text
Python 3.13.14
```

If `python --version` does not work but `py --version` works, that is acceptable. Use `py` in the commands below.

---

## 2. If pip is missing

If this command fails:

```powershell
py -m pip --version
```

or shows:

```text
No module named pip
```

run:

```powershell
py -m ensurepip --upgrade
py -m pip install --upgrade pip
```

Then verify:

```powershell
py -m pip --version
```

---

## 3. Install Git and GitHub CLI

Install these on the Windows test machine so the app can later be updated from GitHub instead of manually copying ZIP files.

Open PowerShell and check if `winget` is available:

```powershell
winget --version
```

If `winget` works, install Git for Windows and GitHub CLI:

```powershell
winget install --id Git.Git -e
winget install --id GitHub.cli -e
```

Close PowerShell, open a new PowerShell window, then verify:

```powershell
git --version
gh --version
```

Configure the Git identity for commits from this machine:

```powershell
git config --global user.name "Websonora"
git config --global user.email "websonora@gmail.com"
```

Authenticate GitHub CLI:

```powershell
gh auth login
```

Recommended choices during login:

```text
GitHub.com
HTTPS
Authenticate Git with your GitHub credentials: Yes
Login with a web browser
```

After browser login, verify:

```powershell
gh auth status
```

If `winget` is not available, install manually:

```text
Git for Windows: https://git-scm.com/download/win
GitHub CLI: https://cli.github.com/
```

After manual install, open a new PowerShell window and run the same verification commands:

```powershell
git --version
gh --version
gh auth login
gh auth status
```

### GitHub repository for app versions

The app version repository is:

```text
https://github.com/websonora/taxtool
```

After GitHub is working on this Windows machine, future updates should come from GitHub.

For a first GitHub-based install, clone into the Websonora folder:

```powershell
mkdir C:\Websonora
cd C:\Websonora
gh repo clone websonora/taxtool tax-document-backup-portal-windows-test
cd C:\Websonora\tax-document-backup-portal-windows-test
```

For future app updates, use:

```powershell
cd C:\Websonora\tax-document-backup-portal-windows-test
git pull
```

If the folder was originally created from a ZIP, keep using the ZIP until Godzilla confirms the repository has been pushed to GitHub. After that, replace the ZIP folder with a fresh `gh repo clone` copy.

---

## 4. Copy/extract the app

Extract the app ZIP into:

```text
C:\Websonora\tax-document-backup-portal-windows-test
```

Expected files/folders:

```text
C:\Websonora\tax-document-backup-portal-windows-test\app
C:\Websonora\tax-document-backup-portal-windows-test\tests
C:\Websonora\tax-document-backup-portal-windows-test\pyproject.toml
C:\Websonora\tax-document-backup-portal-windows-test\README.md
```

Open PowerShell and go to the app folder:

```powershell
cd C:\Websonora\tax-document-backup-portal-windows-test
```

Confirm files:

```powershell
dir
```

---

## 5. Create the virtual environment

From the app folder:

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation with a script execution policy error, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

When prompted, type:

```text
Y
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation works, the prompt should start with:

```text
(.venv)
```

Alternative: if activation is blocked or confusing, you can use the virtual environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip --version
```

---

## 6. Install dependencies

Install the app and test tools:

```powershell
py -m pip install -e . pytest httpx
```

If using the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e . pytest httpx
```

Fallback only: if editable install fails for any reason, install dependencies directly:

```powershell
py -m pip install fastapi "uvicorn[standard]" python-multipart PyMuPDF pytest httpx
```

---

## 7. Create safe test folders

Create a test document root:

```powershell
mkdir C:\TaxPortalTest
mkdir "C:\TaxPortalTest\Cliente Actual"
mkdir C:\TaxPortalTest\2024
mkdir C:\TaxPortalTest\2025
mkdir C:\TaxPortalTest\2026
```

Put at least one test PDF into:

```text
C:\TaxPortalTest\2024
```

Example:

```text
C:\TaxPortalTest\2024\Juan Garcia.pdf
```

Do not use real client documents for initial testing.

---

## 8. Set the document root

In PowerShell, from the app folder:

```powershell
$env:TAX_PORTAL_DOCUMENT_ROOT="C:\TaxPortalTest"
```

This tells the app to search and save inside:

```text
C:\TaxPortalTest
```

---

## 9. Start the app

From the app folder:

```powershell
py -m uvicorn app.main:app --host 127.0.0.1 --port 8088
```

If using the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8088
```

Expected output:

```text
Uvicorn running on http://127.0.0.1:8088
```

Keep this PowerShell window open. The app stops if this window is closed.

---

## 10. Open the app

Open Chrome or Edge and go to:

```text
http://127.0.0.1:8088
```

Health check:

```text
http://127.0.0.1:8088/api/health
```

Do not type the raw URL directly into PowerShell unless using `start` or `Invoke-WebRequest`.

Correct PowerShell examples:

```powershell
start http://127.0.0.1:8088
start http://127.0.0.1:8088/api/health
Invoke-WebRequest http://127.0.0.1:8088/api/health
```

---

## 11. Test the current workflow

In the app:

1. Choose **Income tax season**.
   - For the `2025 season`, the app searches the `2024` backup folder.
   - For the `2026 season`, the app searches the `2025` backup folder.
2. Search for part of the test PDF name, for example `Juan`.
3. Open last year's backup PDF.
4. Use **Preview** to inspect pages.
5. Use **Mark Delete** only on old pages that should not carry forward.
6. Add/upload current-season PDFs if needed.
7. Create the backup PDF.
8. Confirm the output appears in the selected season folder. For the `2025 season`:

```text
C:\TaxPortalTest\2025
```

For the `2026 season`, the final PDF saves under:

```text
C:\TaxPortalTest\2026
```

---

## Troubleshooting

### `pip` is not recognized

Use:

```powershell
py -m pip install fastapi "uvicorn[standard]" python-multipart PyMuPDF pytest httpx
```

or:

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" python-multipart PyMuPDF pytest httpx
```

### `python` is not recognized

Use:

```powershell
py --version
```

and use `py` for all commands.

### PowerShell blocks `.venv` activation

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Website does not open

Make sure the app server is running and showing:

```text
Uvicorn running on http://127.0.0.1:8088
```

You need either:

- Window 1: PowerShell running Uvicorn
- Window 2 or browser: open the website

### Port 8088 already in use

Error:

```text
[WinError 10048] only one usage of each socket address is normally permitted
```

This means another copy of the app is already running on port `8088`.

Check:

```powershell
netstat -ano | findstr :8088
```

Either open the existing app at:

```text
http://127.0.0.1:8088
```

or use another port:

```powershell
py -m uvicorn app.main:app --host 127.0.0.1 --port 8089
```

Then open:

```text
http://127.0.0.1:8089
```

### Git or GitHub CLI installed but still not recognized

If PowerShell shows this after installation:

```text
git : The term 'git' is not recognized
gh : The term 'gh' is not recognized
```

first close **all** PowerShell windows and open a new PowerShell window. Then test:

```powershell
git --version
gh --version
```

If they still do not work, check the common install locations:

```powershell
Test-Path "C:\Program Files\Git\cmd\git.exe"
Test-Path "C:\Program Files\GitHub CLI\gh.exe"
```

If both return `True`, add them to the current user's PATH:

```powershell
$oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
$addPath = "C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI"
[Environment]::SetEnvironmentVariable("Path", "$oldPath;$addPath", "User")
```

Close PowerShell again, open a new PowerShell window, then verify:

```powershell
git --version
gh --version
```

If either `Test-Path` returns `False`, reinstall that tool manually:

```text
Git for Windows: https://git-scm.com/download/win
GitHub CLI: https://cli.github.com/
```

During Git for Windows setup, choose the option that allows Git to be used from the command line / third-party software.

---

## Current limitation

The current app can test:

```text
Prior-year PDF search/open
Preview pages
Mark pages to delete
Merge with uploaded current-year PDFs
Save to selected year folder
```

The next development operation should add the full `Cliente Actual` workflow:

```text
Open current scanned PDF from Cliente Actual first
Preview/delete pages from current scan
Search/open prior-year PDF
Preview/delete pages from old PDF
Merge both cleaned PDFs
Save final PDF into current-year folder using the client filename
```

---

## Production caution

Keep the app local/LAN-only. Do not expose it to the public internet.

For production, prefer a stable document root such as:

```text
C:\Income Tax Reports
```

or a UNC share:

```text
\\SERVER\Income Tax Reports
```

Mapped drives like `T:\` may work when running manually under the staff Windows account, but can fail later if the app is run as a Windows service.
