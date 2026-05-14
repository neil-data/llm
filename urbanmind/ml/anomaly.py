import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from collections import deque
import time

class AnomalyDetector:
    """
    Online anomaly detection using Isolation Forest.
    Trains incrementally as new sensor readings arrive.
    Used by the safety and energy agents as a secondary signal.
    """
    def __init__(self, window: int = 200, contamination: float = 0.05):
        self.window = window
        self.contamination = contamination
        self.buffer: deque = deque(maxlen=window)
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
        self.trained = False

    def add(self, features: list[float]):
        self.buffer.append(features)
        # Retrain every 50 new samples once we have 100+
        if len(self.buffer) >= 100 and len(self.buffer) % 50 == 0:
            self._train()

    def _train(self):
        X = np.array(list(self.buffer))
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled)
        self.trained = True

    def predict(self, features: list[float]) -> dict:
        if not self.trained:
            return {"anomaly": False, "score": 0.0, "note": "model not trained yet"}
        X = np.array(features).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        score = float(self.model.decision_function(X_scaled)[0])
        is_anomaly = self.model.predict(X_scaled)[0] == -1
        return {
            "anomaly": bool(is_anomaly),
            "score": round(score, 4),      # more negative = more anomalous
            "note": "anomaly detected" if is_anomaly else "normal",
        }


# Singleton detectors per domain
traffic_detector = AnomalyDetector()
energy_detector = AnomalyDetector()
environment_detector = AnomalyDetector()


def feed_traffic(reading: dict) -> dict:
    features = [
        reading.get("vehicle_density", 0),
        reading.get("avg_speed_kmh", 50),
        float(reading.get("incident", False)),
    ]
    traffic_detector.add(features)
    return traffic_detector.predict(features)


def feed_energy(reading: dict) -> dict:
    features = [
        reading.get("grid_load_pct", 50),
        reading.get("voltage_v", 230),
        reading.get("kwh_consumed", 400),
        reading.get("renewable_pct", 20),
    ]
    energy_detector.add(features)
    return energy_detector.predict(features)


def feed_environment(reading: dict) -> dict:
    features = [
        reading.get("aqi", 50),
        reading.get("noise_db", 60),
        reading.get("temp_c", 25),
        reading.get("humidity_pct", 60),
    ]
    environment_detector.add(features)
    return environment_detector.predict(features)
