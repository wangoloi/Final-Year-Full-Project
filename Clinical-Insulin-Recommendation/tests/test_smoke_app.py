"""Smoke tests for the FastAPI app (no ML bundle required for liveness)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Repo root (parent of tests/)
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend" / "src"))

# Align DB paths with production app before importing app
import insulin_system.storage.db as _db

_db.set_project_root(_ROOT)


@pytest.fixture()
def client():
    import app as app_module
    from fastapi.testclient import TestClient

    with TestClient(app_module.app) as c:
        yield c


def test_health_live_ok(client):
    r = client.get("/api/health/live")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("live") is True


def test_health_readiness_returns_json_200(client):
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "status" in body
    assert "database" in body


def test_root_or_docs_available(client):
    r = client.get("/docs")
    assert r.status_code == 200
