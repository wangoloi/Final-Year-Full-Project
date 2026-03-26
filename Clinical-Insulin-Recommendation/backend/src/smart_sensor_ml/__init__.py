"""
Smart Sensor Diabetes Monitoring — end-to-end ML pipeline (insulin dose tier prediction).

Train classifiers to predict Low / Moderate / High insulin-dose need tiers from sensor
and lifestyle features, with optional LSTM on patient sequences.
"""

from smart_sensor_ml.persistence import load_model, predict_new_data, save_model
from smart_sensor_ml.recommend import recommend

__all__ = [
    "load_model",
    "predict_new_data",
    "save_model",
    "recommend",
]
