"""Runtime readiness state for Meal Plan API startup warmup."""
from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any

_lock = Lock()
_state: dict[str, Any] = {}


def reset() -> None:
    with _lock:
        _state.clear()
        _state.update(
            {
                "status": "starting",
                "stages": {
                    "config": {"status": "pending"},
                    "database": {"status": "pending"},
                    "foods": {"status": "pending"},
                    "rag": {"status": "pending"},
                    "typesense": {"status": "pending"},
                },
                "warnings": [],
            }
        )


def set_stage(stage: str, status: str, detail: str | None = None, **extra: Any) -> None:
    with _lock:
        _state.setdefault("stages", {})
        current = _state["stages"].setdefault(stage, {})
        current["status"] = status
        if detail is not None:
            current["detail"] = detail
        if extra:
            current.update(extra)


def set_status(status: str, detail: str | None = None) -> None:
    with _lock:
        _state["status"] = status
        if detail is not None:
            _state["detail"] = detail


def set_warnings(warnings: list[str]) -> None:
    with _lock:
        _state["warnings"] = list(warnings)


def snapshot() -> dict[str, Any]:
    with _lock:
        return deepcopy(_state)


def is_ready() -> bool:
    with _lock:
        return _state.get("status") == "ready"


reset()
