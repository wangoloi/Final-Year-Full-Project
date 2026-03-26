"""8. Rule-based recommendations from predicted insulin tier / risk."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def recommend(
    predicted_tier_name: str,
    glucose_level: Optional[float] = None,
    *,
    time_category: Optional[str] = None,
    meal_context: Optional[str] = None,
    activity_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Structured guidance keyed off model tier (proxy for insulin need intensity).

    High tier → emphasize medical follow-up + structured lifestyle review.
    Moderate → prevention and monitoring.
    Low → maintenance habits.
    """
    tier = (predicted_tier_name or "").strip().lower()
    out: Dict[str, Any] = {
        "tier": predicted_tier_name,
        "summary": "",
        "actions": [],
        "medical": [],
        "lifestyle": [],
    }

    if tier == "high":
        out["summary"] = (
            "Model suggests higher insulin-dose tier for this context. Prioritize safety and clinician review."
        )
        out["medical"] = [
            "Schedule a timely review with your diabetes care team to align insulin plan with CGM/wearable data.",
            "Discuss correction factors and any nocturnal patterns (e.g., dawn phenomenon) shown in time-of-day features.",
        ]
        out["lifestyle"] = [
            "Track meals and activity consistently; pair carbs with protein/fiber where appropriate.",
            "Prioritize sleep regularity and stress reduction — both affect glucose variability.",
        ]
        out["actions"] = ["Book clinical follow-up", "Export recent sensor trends for the visit", "Avoid aggressive dose changes without guidance"]
    elif tier == "moderate":
        out["summary"] = "Moderate insulin-dose tier — preventive tuning and monitoring are most useful."
        out["medical"] = [
            "Plan routine labs and HbA1c checks as advised by your clinician.",
            "Ask whether post-meal spikes or activity-related lows need pattern-specific adjustments.",
        ]
        out["lifestyle"] = [
            "Maintain regular physical activity and step goals aligned with your care plan.",
            "Improve diet quality score patterns (balanced plates, consistent timing).",
        ]
        out["actions"] = ["Weekly review of glucose trends", "Adjust snacks around exercise with clinician rules"]
    else:
        out["summary"] = "Lower modeled insulin-dose tier — focus on sustaining stable routines."
        out["medical"] = [
            "Continue periodic check-ins per your provider’s schedule.",
            "Report unexpected lows or persistent highs even if overall tier looks low.",
        ]
        out["lifestyle"] = [
            "Keep current sleep, activity, and meal patterns that are working.",
            "Stay hydrated and keep consistent meal timing where possible.",
        ]
        out["actions"] = ["Maintain monitoring habits", "Reassess if illness, medications, or weight change"]

    if glucose_level is not None:
        try:
            g = float(glucose_level)
            if g < 70:
                out["medical"].insert(0, "Current glucose looks low — follow your hypoglycemia plan and treat per clinician instructions.")
            elif g > 250:
                out["medical"].insert(0, "Current glucose is very high — seek urgent-care guidance if you have symptoms or ketones per your plan.")
        except (TypeError, ValueError):
            pass

    tc = (time_category or "").strip().lower()
    meal = (meal_context or "").strip().lower()
    act = (activity_context or "").strip().lower()
    if tc == "night" and tier == "high":
        out["lifestyle"].append(
            "Night-time higher tier: consider monitoring overnight trends and discussing basal timing with your clinician (educational)."
        )
    if meal == "after_meal" and glucose_level is not None:
        try:
            if float(glucose_level) > 180:
                out["lifestyle"].append(
                    "After-meal context with elevated glucose: dietary review and meal timing may help (educational guidance)."
                )
        except (TypeError, ValueError):
            pass
    if act == "post_exercise" and glucose_level is not None:
        try:
            if float(glucose_level) < 100:
                out["medical"].insert(0, "Post-exercise with lower glucose: follow hypo precautions per your plan.")
        except (TypeError, ValueError):
            pass

    return out
