# Running the integrated version

The bridge and React frontend are on `integrate-prototype`; the untouched Streamlit fallback is on `goldfish-prototype`. Keep them in separate worktrees so all three can run at once.

## One-time setup

From the `integrate-prototype` checkout, create a sibling worktree for the prototype branch (skip this if you already have that checkout there):

```powershell
git worktree add ..\goldfish-prototype goldfish-prototype
```

In the `goldfish-prototype` worktree, prepare the fictional vault and a Python environment for both Python apps:

```powershell
Set-Location C:\Users\User\goldfish-prototype
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r ..\goldfish-app\bridge\requirements.txt
if (-not (Test-Path .\GoldfishVault)) { .\.venv\Scripts\python.exe .\make_vault.py }
```

If you already use a different local notes folder, point `NOTES_ROOT` to it instead of the demo vault. The bridge defaults to `.\GoldfishVault` relative to its working directory.

Install frontend packages once from `C:\Users\User\goldfish-app\frontend` with `npm ci`. Create `frontend\.env.local` from `.env.example` if needed, then set:

```dotenv
VITE_USE_MOCKS=false
VITE_API_BASE=http://127.0.0.1:8000
```

## Start each app in its own PowerShell terminal

**1. Bridge**, from the `integrate-prototype` checkout:

```powershell
Set-Location C:\Users\User\goldfish-app
$env:NOTES_ROOT = (Resolve-Path ..\goldfish-prototype\GoldfishVault).Path
..\goldfish-prototype\.venv\Scripts\python.exe -m uvicorn bridge.main:app --host 127.0.0.1 --port 8000
```

**2. React frontend:**

```powershell
Set-Location C:\Users\User\goldfish-app\frontend
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. To use mocks instead, change `VITE_USE_MOCKS=true` in `.env.local` and restart Vite.

**3. Streamlit fallback**, from its worktree:

```powershell
Set-Location C:\Users\User\goldfish-prototype
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`. For Streamlit's local-model features, start LM Studio with a model loaded and its local server available on port `1234` or `1235`.

The bridge and Streamlit app are configured for offline model use; the integrated app's API and UI communicate through localhost. Both Python apps require `sentence-transformers/all-MiniLM-L6-v2` to already be cached locally. This machine did not have those weights cached: bridge Ask returns an offline-model error, and Streamlit displays a startup exception. No download is attempted automatically. Verify fully offline operation only after required models are already present.
