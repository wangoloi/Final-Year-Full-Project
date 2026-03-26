# Removing a *legacy Node* `backend/` folder (Windows)

**Note:** The project’s **real** Python API now lives in **`backend/`** (FastAPI). Do **not** delete that.

If you still have an **old** folder that contained only **Node `node_modules`** (no `backend/api/`, no `backend/run.py`), that was obsolete. The app uses **`backend/`** (Python) + **`frontend/`** (Vite).

Deletion can fail with *“being used by another process”* if:

- Cursor/VS Code or Explorer has that folder open  
- Antivirus is scanning it  

**Fix:** close the IDE tab pointing inside `backend/`, then in PowerShell from repo root:

```powershell
Remove-Item -LiteralPath .\backend -Recurse -Force
```

Or delete it from File Explorer after closing programs that might lock it.
