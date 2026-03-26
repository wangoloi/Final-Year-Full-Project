"""
Database backup and restore.
Safe storage with timestamped backups, easy retrieval.
"""
from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .db import get_db_path

logger = logging.getLogger(__name__)

BACKUP_DIR_NAME = "backups"


def get_backup_dir(db_path: Optional[Path] = None) -> Path:
    """Return the backups directory (sibling to the database)."""
    path = get_db_path(db_path)
    return path.parent / BACKUP_DIR_NAME


def create_backup(db_path: Optional[Path] = None) -> Optional[Path]:
    """
    Create a timestamped copy of the database.
    Returns path to backup file, or None on failure.
    """
    path = get_db_path(db_path)
    if not path.exists():
        return None
    backup_dir = get_backup_dir(db_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"glucosense_{ts}.db"
    try:
        shutil.copy2(path, dest)
        logger.info("Backup created: %s", dest)
        return dest
    except Exception as e:
        logger.error("Backup failed: %s", e)
        return None


def list_backups(db_path: Optional[Path] = None) -> List[dict]:
    """Return list of backup files with metadata (path, size, created)."""
    backup_dir = get_backup_dir(db_path)
    if not backup_dir.exists():
        return []
    out = []
    for f in sorted(backup_dir.glob("glucosense_*.db"), reverse=True):
        try:
            stat = f.stat()
            out.append({
                "filename": f.name,
                "path": str(f),
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        except Exception:
            pass
    return out


def restore_backup(filename: str, db_path: Optional[Path] = None) -> bool:
    """
    Restore database from a backup file.
    Copies backup over current db. Returns True on success.
    """
    path = get_db_path(db_path)
    backup_dir = get_backup_dir(db_path)
    source = backup_dir / filename
    if not source.exists() or not source.is_file():
        return False
    try:
        shutil.copy2(source, path)
        logger.info("Restored from backup: %s", filename)
        return True
    except Exception as e:
        logger.error("Restore failed: %s", e)
        return False
