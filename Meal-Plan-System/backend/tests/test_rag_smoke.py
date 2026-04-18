"""Ensure ChromaDB imports cleanly with pinned NumPy (RAG stack)."""
import subprocess
import sys


def test_chromadb_imports_with_pinned_numpy():
    """Fails in CI if ChromaDB breaks against NumPy (e.g. np.float_ removed in NumPy 2)."""
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; os.environ.setdefault('ANONYMIZED_TELEMETRY','false'); "
            "import chromadb; print('ok')",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout or "chromadb import failed"
