"""
Load clinical thresholds and Uganda T1D guidelines from JSON config files.

Falls back to hardcoded defaults if config files are missing or invalid.
Config path: project_root/config/clinical_thresholds.json, config/uganda_t1d_guidelines.json
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default paths relative to repository root (…/backend/src/insulin_system/config → parents[4])
_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"
_CLINICAL_THRESHOLDS_PATH = _CONFIG_DIR / "clinical_thresholds.json"
_UGANDA_GUIDELINES_PATH = _CONFIG_DIR / "uganda_t1d_guidelines.json"

# Cached configs
_clinical_thresholds: Optional[Dict[str, Any]] = None
_uganda_guidelines: Optional[Dict[str, Any]] = None


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file if it exists."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load config %s: %s", path, e)
        return None


def get_clinical_thresholds() -> Dict[str, Any]:
    """Load clinical thresholds from JSON. Returns cached or empty dict."""
    global _clinical_thresholds
    if _clinical_thresholds is None:
        _clinical_thresholds = _load_json(_CLINICAL_THRESHOLDS_PATH) or {}
    return _clinical_thresholds


def get_uganda_guidelines() -> Dict[str, Any]:
    """Load Uganda T1D guidelines from JSON. Returns cached or empty dict."""
    global _uganda_guidelines
    if _uganda_guidelines is None:
        _uganda_guidelines = _load_json(_UGANDA_GUIDELINES_PATH) or {}
    return _uganda_guidelines


def _get_nested(cfg: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Get nested value from dict."""
    d = cfg
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def get_threshold(section: str, key: str, default: Any = None) -> Any:
    """Get a single threshold value from clinical_thresholds.json."""
    cfg = get_clinical_thresholds()
    return _get_nested(cfg, section, key, default=default)


def get_glucose_threshold(key: str, default: Any = None) -> Any:
    """Convenience: get glucose_mgdl threshold."""
    return get_threshold("glucose_mgdl", key, default)


def get_uganda_daily_dose_range() -> tuple:
    """Return (min_iu_per_kg, max_iu_per_kg) from Uganda guidelines."""
    g = get_uganda_guidelines()
    dd = g.get("daily_insulin_dose", {})
    return (
        float(dd.get("iu_per_kg_min", 0.6)),
        float(dd.get("iu_per_kg_max", 1.5)),
    )


def get_uganda_children_under_5() -> tuple:
    """Return (iu_per_kg, age_years) for children <5. Refer to paediatrician."""
    g = get_uganda_guidelines()
    dd = g.get("daily_insulin_dose", {})
    return (
        float(dd.get("children_under_5_iu_per_kg", 0.5)),
        int(dd.get("children_under_5_age_years", 5)),
    )


def get_uganda_basal_bolus_split() -> tuple:
    """Return (basal_min_fraction, basal_max_fraction) for evening dose. Default 40-50%."""
    g = get_uganda_guidelines()
    bb = g.get("regimens", {}).get("basal_bolus", {}).get("basal_portion", {})
    return (
        float(bb.get("evening_min_fraction", 0.4)),
        float(bb.get("evening_max_fraction", 0.5)),
    )


def get_uganda_premixed_split() -> tuple:
    """Return (morning_fraction, evening_fraction) for twice-daily premixed. Default 2/3, 1/3."""
    g = get_uganda_guidelines()
    pm = g.get("regimens", {}).get("premixed_twice_daily", {})
    return (
        float(pm.get("morning_fraction_value", 0.667)),
        float(pm.get("evening_fraction_value", 0.333)),
    )
