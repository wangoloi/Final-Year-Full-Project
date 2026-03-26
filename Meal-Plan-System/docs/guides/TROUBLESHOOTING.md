# Troubleshooting Guide - OneDrive Database Issues

> **Current Meal Plan stack:** **FastAPI** in `backend/`. Default SQLite: **Windows** → `%LocalAppData%\Glocusense\glocusense.db` · **Linux/mac** → `backend/instance/glocusense.db`. Sections below that mention Flask or a root `instance/` folder are **legacy**; prefer [HOW_TO_RUN.md](./HOW_TO_RUN.md).

## Problem: "unable to open database file" Error

If you're getting this error on Windows, especially with OneDrive, here are solutions:

### Solution 1: Pause OneDrive Sync (Quick Fix)

1. Right-click the OneDrive icon in system tray
2. Click "Pause syncing" → "2 hours"
3. Run `python init_db.py` again
4. Resume OneDrive sync after database is created

### Solution 2: Move Project Outside OneDrive

1. Copy the entire project folder to a location outside OneDrive (e.g., `C:\Projects\`)
2. Navigate to the new location
3. Run `python init_db.py`

### Solution 3: Exclude Database from OneDrive Sync

1. Right-click the `instance` folder
2. Select "OneDrive" → "Free up space" or "Always keep on this device"
3. Or add `instance/` to OneDrive exclusion list

### Solution 4: Use Relative Path (Alternative)

If the above don't work, you can modify the database path to use a relative path:

Edit `app/__init__.py` and change:
```python
# Change from absolute to relative path
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'sqlite:///instance/glocusense.db'  # Relative path
)
```

### Solution 5: Run as Administrator

1. Right-click PowerShell/Command Prompt
2. Select "Run as Administrator"
3. Navigate to project folder
4. Run `python init_db.py`

### Solution 6: Check File Permissions

```powershell
# Check if you can write to the instance directory
Test-Path -Path "instance" -PathType Container
# Should return True

# Try creating a test file
New-Item -Path "instance\test.txt" -ItemType File
# If this fails, there's a permission issue
```

### Solution 7: Use Environment Variable

Create a `.env` file in project root:
```env
DATABASE_URL=sqlite:///./instance/glocusense.db
```

This uses a relative path that might work better with OneDrive.

---

## Why This Happens

OneDrive can lock files during sync operations, preventing SQLite from creating or accessing the database file. The solutions above work around this limitation.

---

## Recommended Solution

**For development:** Move project outside OneDrive or pause sync temporarily.

**For production:** Use a proper database server (PostgreSQL, MySQL) instead of SQLite.

