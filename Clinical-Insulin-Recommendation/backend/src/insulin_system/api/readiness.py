from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Dict

from fastapi.responses import JSONResponse

_lock = Lock()
_state: Dict[str, Any] = {}


def reset_readiness() -> None:
    with _lock:
        _state.clear()
        _state.update(
            {
                "status": "starting",
                "database": {"status": "pending"},
                "runtime": {"status": "pending"},
                "details": {},
            }
        )


def update_readiness(**updates: Any) -> None:
    with _lock:
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(_state.get(key), dict):
                _state[key].update(value)
            else:
                _state[key] = value


def get_readiness() -> Dict[str, Any]:
    with _lock:
        return deepcopy(_state)


def ready_response() -> JSONResponse:
    state = get_readiness()
    status_code = 200 if state.get("status") == "ready" else 503
    return JSONResponse(status_code=status_code, content=state)


reset_readiness()
