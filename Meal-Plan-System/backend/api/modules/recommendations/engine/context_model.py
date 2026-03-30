"""
Stage 1: Glucose State Model — trend, stability, risk (educational heuristics).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from api.models import GlucoseReading


@dataclass
class GlucoseStateModel:
    """Structured health context for downstream stages."""

    state: str
    trend: str  # increasing | decreasing | flat
    stability: str  # stable | unstable | unknown
    risk_score: float  # 0..1
    readings_analyzed: int
    latest_mg_dl: Optional[float]
    avg_recent_mg_dl: Optional[float]
    short_term_slope: float  # mg/dL per step (newer - older) / steps
    variance: Optional[float]


def _variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return sum((x - m) ** 2 for x in values) / len(values)


def _slope_last_three(vals_newest_first: List[float]) -> float:
    """Vals: index 0 = newest. Approximate slope per reading step (positive = rising)."""
    if len(vals_newest_first) < 2:
        return 0.0
    v = vals_newest_first[:3]
    if len(v) == 2:
        return (v[0] - v[1])
    # three points: newest v0, mid v1, oldest v2
    return (v[0] - v[2]) / 2.0


def infer_glucose_state(readings: List[GlucoseReading]) -> Tuple[GlucoseStateModel, Dict[str, Any]]:
    """
    Build glucose state from recent readings (newest first).
    Risk combines level, trend, and variability.
    """
    if not readings:
        gsm = GlucoseStateModel(
            state="unknown_no_data",
            trend="flat",
            stability="unknown",
            risk_score=0.35,
            readings_analyzed=0,
            latest_mg_dl=None,
            avg_recent_mg_dl=None,
            short_term_slope=0.0,
            variance=None,
        )
        ctx = {
            "rationale": (
                "No blood glucose readings yet. Log readings so the engine can estimate trend, stability, and risk."
            ),
            "meal_logic": "Defaulting to conservative GI and fiber targets from your profile.",
        }
        return gsm, ctx

    n = min(10, len(readings))
    vals = [r.reading_value for r in readings[:n]]
    latest = vals[0]
    avg_recent = sum(vals) / len(vals)
    var = _variance(vals)
    slope = _slope_last_three(vals)

    if slope > 8:
        trend = "increasing"
    elif slope < -8:
        trend = "decreasing"
    else:
        trend = "flat"

    # Stability: coefficient of variation inspired
    cv = (math.sqrt(var) / avg_recent) if avg_recent and avg_recent > 1e-6 else 0.0
    if len(vals) < 3:
        stability = "unknown"
    elif cv < 0.12 and var < 400:
        stability = "stable"
    else:
        stability = "unstable"

    # Risk 0..1 from level + trend + volatility
    level_risk = min(1.0, max(0.0, (latest - 90) / 180))
    trend_risk = 0.15 if trend == "increasing" else (0.05 if trend == "decreasing" else 0.0)
    vol_risk = min(0.25, cv * 0.8)
    risk_score = min(1.0, 0.15 + 0.55 * level_risk + trend_risk + vol_risk)

    blended = 0.55 * latest + 0.45 * avg_recent

    if blended < 65:
        state = "falling_low"
    elif blended >= 260 or latest >= 300:
        state = "critical_high"
    elif blended >= 200 or latest >= 240:
        state = "rising_high"
    elif trend == "increasing" and blended >= 150:
        state = "rising_high"
    elif blended >= 180:
        state = "elevated"
    elif 70 <= blended <= 170 and stability == "stable":
        state = "stable_controlled"
    elif trend == "decreasing" and blended <= 180:
        state = "improving"
    else:
        state = "stable_controlled"

    rationale = _rationale_for(state, trend, stability, latest, blended)
    meal_logic = _meal_logic_for(state, trend)

    gsm = GlucoseStateModel(
        state=state,
        trend=trend,
        stability=stability,
        risk_score=round(risk_score, 3),
        readings_analyzed=len(vals),
        latest_mg_dl=round(latest, 1),
        avg_recent_mg_dl=round(avg_recent, 1),
        short_term_slope=round(slope, 2),
        variance=round(var, 2) if var else None,
    )
    ctx = {
        "rationale": rationale,
        "meal_logic": meal_logic,
    }
    return gsm, ctx


def _rationale_for(state: str, trend: str, stability: str, latest: float, blended: float) -> str:
    parts = [
        f"Latest {latest:.0f} mg/dL (blended recent ~{blended:.0f} mg/dL).",
        f"Short-term trend: {trend}.",
        f"Variability: {stability}.",
    ]
    if state == "critical_high":
        parts.append("Pattern suggests elevated risk — prioritize minimal glycemic load and clinician guidance.")
    elif state == "rising_high":
        parts.append("Levels are high or rising; the engine tightens carb and GI constraints.")
    elif state == "falling_low":
        parts.append("Levels are on the low side; balance structured carbs with protein per your care plan.")
    elif state == "improving":
        parts.append("Recent trend is improving; balanced low–moderate GI meals remain appropriate.")
    else:
        parts.append("Pattern is relatively controlled; recommendations focus on steady, fiber-forward choices.")
    return " ".join(parts)


def _meal_logic_for(state: str, trend: str) -> str:
    if state in ("critical_high", "rising_high", "elevated"):
        return "Strict dynamic GI cap, higher fiber floor, penalize high carbs; prefer diabetes-friendly catalog items."
    if state == "falling_low":
        return "Include moderate carb bands with protein emphasis; avoid extreme GI-only restriction."
    if trend == "decreasing":
        return "Slightly more flexibility while maintaining balanced macros and fiber."
    return "Weight glycemic impact, fiber, and protein balance; diversify categories across the week."


def glucose_state_to_dict(gsm: GlucoseStateModel) -> Dict[str, Any]:
    return {
        "state": gsm.state,
        "trend": gsm.trend,
        "stability": gsm.stability,
        "risk_score": gsm.risk_score,
        "readings_analyzed": gsm.readings_analyzed,
        "latest_mg_dl": gsm.latest_mg_dl,
        "avg_recent_mg_dl": gsm.avg_recent_mg_dl,
        "short_term_slope": gsm.short_term_slope,
        "variance": gsm.variance,
    }
