from __future__ import annotations

from typing import Any

import numpy as np

from contracts import ModelResult
from model_registry import ModelRegistry


class ModelRunner:
	DEFAULT_ANOMALY_THRESHOLD = 0.5

	FEATURE_ORDER = [
		# Raw sensor readings
		"temperature",
		"humidity",
		"motion",
		"light_lux",
		# Derived scalar
		"heat_index",
		# Rolling-window statistics
		"temp_rolling_mean",
		"temp_rolling_std",
		"temp_z_score",
		# Temporal / sequential features
		"temp_delta",   # rate of change vs. previous reading
		"temp_lag_1",   # previous raw temperature
		"temp_ema",     # exponentially-weighted moving average
	]

	def __init__(self, registry: ModelRegistry):
		self.registry = registry
		self.model, self.model_version = self.registry.load_active()
		self.anomaly_threshold = self.registry.load_active_anomaly_threshold(self.DEFAULT_ANOMALY_THRESHOLD)

	def reload_active_model(self) -> None:
		self.model, self.model_version = self.registry.load_active()
		self.anomaly_threshold = self.registry.load_active_anomaly_threshold(self.DEFAULT_ANOMALY_THRESHOLD)

	def _vectorize(self, data: dict[str, Any]) -> np.ndarray:
		values: list[float] = []
		for feature in self.FEATURE_ORDER:
			value = data.get(feature, 0.0)
			if isinstance(value, bool):
				values.append(float(int(value)))
			else:
				values.append(float(value))
		return np.asarray(values, dtype=float).reshape(1, -1)

	def predict(self, data: dict[str, Any]) -> ModelResult:
		if self.model is None:
			score = min(abs(float(data.get("temp_z_score", 0.0))) / 5.0, 1.0)
			label = "anomaly" if score >= self.anomaly_threshold else "normal"
			return ModelResult(
				model_version="none",
				score=score,
				label=label,
				confidence=score,
			)

		vector = self._vectorize(data)
		if hasattr(self.model, "predict_proba"):
			probabilities = self.model.predict_proba(vector)[0]
			score = float(probabilities[-1])
		elif hasattr(self.model, "decision_function"):
			raw_score = float(self.model.decision_function(vector)[0])
			score = 1.0 / (1.0 + np.exp(-raw_score))
		else:
			prediction = int(self.model.predict(vector)[0])
			score = float(prediction)

		label = "anomaly" if score >= self.anomaly_threshold else "normal"
		confidence = score if label == "anomaly" else (1.0 - score)
		return ModelResult(
			model_version=self.model_version,
			score=score,
			label=label,
			confidence=confidence,
		)

