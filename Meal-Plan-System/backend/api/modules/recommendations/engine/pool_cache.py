"""In-process TTL cache for candidate pool *snapshots* (food ids + pool labels), rehydrated per request."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

_CACHE: Dict[str, tuple] = {}
_TTL_SEC = 60.0


def _key(parts: Dict[str, Any]) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_serialized_pool_rows(key_parts: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Returns list of {food_id, pool} in merge order, or None on miss/expiry."""
    k = _key(key_parts)
    ent = _CACHE.get(k)
    if not ent:
        return None
    ts, rows = ent
    if time.monotonic() - ts > _TTL_SEC:
        del _CACHE[k]
        return None
    return rows


def set_serialized_pool_rows(key_parts: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    _CACHE[_key(key_parts)] = (time.monotonic(), rows)


def cache_stats() -> Dict[str, Any]:
    return {"entries": len(_CACHE), "ttl_sec": _TTL_SEC}


def cache_clear() -> None:
    _CACHE.clear()
