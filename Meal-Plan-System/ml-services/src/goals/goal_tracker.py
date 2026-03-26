"""
Goal Tracking System
- Weight, glucose, HbA1c, time-in-range, nutrition, activity goals
- Regression-based prediction
- Milestone detection
- Risk detection for goal failure
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
import numpy as np


@dataclass
class GoalProgress:
    goal_type: str
    target_value: float
    current_value: float
    progress_pct: float
    on_track: bool
    days_remaining: Optional[int]
    risk_level: str  # low, medium, high


def compute_progress_pct(current: float, target: float, goal_type: str) -> float:
    """Compute progress percentage. For weight loss, higher current = lower progress."""
    if target == 0:
        return 0.0
    if goal_type == "weight" and target < current:
        # Weight loss: progress = (start - current) / (start - target) * 100
        return min(100, max(0, 100 * (1 - (current - target) / current)))
    return min(100, max(0, 100 * current / target))


def regression_prediction(
    history: List[float],
    horizon: int = 7,
) -> List[float]:
    """Simple linear regression extrapolation for goal prediction."""
    if len(history) < 2:
        return [history[-1]] * horizon if history else [0.0] * horizon
    x = np.arange(len(history))
    slope = np.polyfit(x, history, 1)[0]
    last = history[-1]
    return [last + slope * (i + 1) for i in range(horizon)]


def detect_milestone(
    current: float,
    target: float,
    milestones: List[float],
) -> Optional[float]:
    """Return next milestone if within reach."""
    for m in sorted(milestones):
        if m <= target and current < m:
            return m
    return None


def assess_risk(
    progress_pct: float,
    days_remaining: Optional[int],
    velocity: Optional[float],
) -> str:
    """Assess risk of goal failure: low, medium, high."""
    if progress_pct >= 90:
        return "low"
    if days_remaining is not None and days_remaining <= 7:
        if progress_pct < 50:
            return "high"
        if progress_pct < 75:
            return "medium"
    if velocity is not None and velocity < 0:
        return "medium"
    return "low"
