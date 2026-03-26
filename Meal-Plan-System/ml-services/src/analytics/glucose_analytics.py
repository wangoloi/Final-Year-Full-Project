"""
Glucose Analytics and Predictive Modeling
- Time series: moving averages, post-meal spike detection
- Time in range, variability metrics
- Correlation: meal-glucose, exercise impact
- LSTM forecasting placeholder
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class GlucoseReading:
    value: float
    timestamp: str
    reading_type: str


def moving_average(readings: List[GlucoseReading], window: int = 7) -> List[float]:
    values = [r.value for r in readings]
    if len(values) < window:
        return values
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(np.mean(values[start : i + 1]))
    return result


def detect_post_meal_spike(
    readings: List[GlucoseReading],
    baseline: float,
    threshold_increase: float = 30,
) -> List[Tuple[int, float]]:
    spikes = []
    for i, r in enumerate(readings):
        if r.value >= baseline + threshold_increase:
            spikes.append((i, r.value))
    return spikes


def time_in_range(
    readings: List[GlucoseReading],
    target_min: float = 70,
    target_max: float = 180,
) -> float:
    if not readings:
        return 0.0
    in_range = sum(1 for r in readings if target_min <= r.value <= target_max)
    return 100.0 * in_range / len(readings)


def variability_metric(readings: List[GlucoseReading]) -> float:
    if len(readings) < 2:
        return 0.0
    values = [r.value for r in readings]
    return float(np.std(values))


def predict_glucose_lstm_placeholder(
    history: List[GlucoseReading],
    horizon: int = 6,
) -> List[float]:
    if not history:
        return [0.0] * horizon
    last = history[-1].value
    return [last] * horizon
