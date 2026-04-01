from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score

from config import Settings, load_settings
from model_registry import ModelRegistry
from state_store import StateStore


@dataclass(slots=True)
class TrainingResult:
	success: bool
	rows_used: int
	metrics: dict[str, float]
	version: str | None = None
	artifact_path: str | None = None
	notes: str = ""


class Trainer:
	FEATURES = [
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

	def __init__(self, settings: Settings):
		self.settings = settings
		self.state_store = StateStore(settings.db_path)
		self.registry = ModelRegistry(settings.model_dir, settings.active_model_file)

	@staticmethod
	def _label_from_record(record: dict) -> int:
		data = record.get("data", {})
		temperature = float(data.get("temperature", 0.0))
		z_score = abs(float(data.get("temp_z_score", 0.0)))
		return int(temperature > 40.0 or z_score >= 2.8)

	def _build_matrix(self, records: list[dict]) -> tuple[np.ndarray, np.ndarray]:
		matrix: list[list[float]] = []
		labels: list[int] = []
		for record in records:
			data = record.get("data", {})
			row: list[float] = []
			for feature in self.FEATURES:
				value = data.get(feature, 0.0)
				if isinstance(value, bool):
					row.append(float(int(value)))
				else:
					row.append(float(value))
			matrix.append(row)
			labels.append(self._label_from_record(record))
		return np.asarray(matrix, dtype=float), np.asarray(labels, dtype=int)

	def run(self) -> TrainingResult:
		records = self.state_store.fetch_telemetry_window(self.settings.retrain_window_hours)
		rows_used = len(records)
		if rows_used < self.settings.retrain_min_rows:
			notes = f"insufficient_rows:{rows_used}"
			self.state_store.save_training_run(status="skipped", rows_used=rows_used, notes=notes)
			return TrainingResult(False, rows_used, {}, notes=notes)

		x, y = self._build_matrix(records)
		if len(np.unique(y)) < 2:
			notes = "single_class_data"
			self.state_store.save_training_run(status="skipped", rows_used=rows_used, notes=notes)
			return TrainingResult(False, rows_used, {}, notes=notes)

		model = RandomForestClassifier(n_estimators=150, random_state=42)
		model.fit(x, y)
		predictions = model.predict(x)
		metrics = {
			"f1": float(f1_score(y, predictions)),
			"anomaly_rate": float(np.mean(y)),
		}

		version, artifact_path = self.registry.register(model=model, model_name="rf_anomaly", metrics=metrics)
		self.state_store.save_model_version(
			model_name="rf_anomaly",
			version=version,
			metrics=metrics,
			artifact_path=artifact_path,
		)
		self.state_store.save_training_run(status="success", rows_used=rows_used, metrics=metrics, notes="")

		return TrainingResult(
			success=True,
			rows_used=rows_used,
			metrics=metrics,
			version=version,
			artifact_path=artifact_path,
		)


if __name__ == "__main__":
	trainer = Trainer(load_settings())
	result = trainer.run()
	print(result)

