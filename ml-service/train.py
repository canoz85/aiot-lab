from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

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
	THRESHOLDS = [0.4, 0.5, 0.6, 0.7]
	TEST_FRACTION = 0.2
	MIN_RECALL_TARGET = 0.9

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

	@staticmethod
	def _threshold_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
		metrics: dict[str, float] = {}
		for threshold in Trainer.THRESHOLDS:
			predictions = (probabilities >= threshold).astype(int)
			key = str(threshold).replace(".", "_")
			metrics[f"thr_{key}_precision"] = float(precision_score(y_true, predictions, zero_division=0))
			metrics[f"thr_{key}_recall"] = float(recall_score(y_true, predictions, zero_division=0))
			metrics[f"thr_{key}_f1"] = float(f1_score(y_true, predictions, zero_division=0))
		return metrics

	@classmethod
	def recommend_threshold(cls, metrics: dict[str, float]) -> tuple[float, str]:
		candidates: list[tuple[float, float, float, float]] = []
		for threshold in cls.THRESHOLDS:
			key = str(threshold).replace(".", "_")
			precision = float(metrics.get(f"thr_{key}_precision", 0.0))
			recall = float(metrics.get(f"thr_{key}_recall", 0.0))
			f1 = float(metrics.get(f"thr_{key}_f1", 0.0))
			candidates.append((threshold, precision, recall, f1))

		meets_recall = [row for row in candidates if row[2] >= cls.MIN_RECALL_TARGET]
		if meets_recall:
			# Prefer highest precision; tie-break with higher threshold.
			best = max(meets_recall, key=lambda row: (row[1], row[0]))
			reason = f"highest_precision_with_recall_ge_{cls.MIN_RECALL_TARGET:.2f}"
		else:
			# If target recall cannot be met, maximize F1.
			best = max(candidates, key=lambda row: (row[3], row[2], row[0]))
			reason = "fallback_best_f1"

		return best[0], reason

	@classmethod
	def _time_split(
		cls,
		x: np.ndarray,
		y: np.ndarray,
	) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
		test_rows = max(1, int(round(len(y) * cls.TEST_FRACTION)))
		if test_rows >= len(y):
			return None

		split_idx = len(y) - test_rows
		x_train, x_test = x[:split_idx], x[split_idx:]
		y_train, y_test = y[:split_idx], y[split_idx:]

		# Both splits need positive/negative samples for stable metrics.
		if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
			return None
		return x_train, x_test, y_train, y_test

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

		time_split = self._time_split(x, y)
		split_note = "split:time"
		if time_split is None:
			try:
				x_train, x_test, y_train, y_test = train_test_split(
					x,
					y,
					test_size=self.TEST_FRACTION,
					random_state=42,
					stratify=y,
				)
				split_note = "split:stratified_fallback"
			except ValueError:
				notes = "split_failed_insufficient_class_support"
				self.state_store.save_training_run(status="skipped", rows_used=rows_used, notes=notes)
				return TrainingResult(False, rows_used, {}, notes=notes)
		else:
			x_train, x_test, y_train, y_test = time_split

		model = RandomForestClassifier(n_estimators=150, random_state=42)
		model.fit(x_train, y_train)
		predictions = model.predict(x_test)
		probabilities = model.predict_proba(x_test)[:, 1]
		tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()
		metrics = {
			"f1": float(f1_score(y_test, predictions, zero_division=0)),
			"precision": float(precision_score(y_test, predictions, zero_division=0)),
			"recall": float(recall_score(y_test, predictions, zero_division=0)),
			"pr_auc": float(average_precision_score(y_test, probabilities)),
			"anomaly_rate": float(np.mean(y)),
			"time_split_used": float(1.0 if split_note == "split:time" else 0.0),
			"train_rows": float(len(y_train)),
			"test_rows": float(len(y_test)),
			"tn": float(tn),
			"fp": float(fp),
			"fn": float(fn),
			"tp": float(tp),
		}
		metrics.update(self._threshold_metrics(y_test, probabilities))
		recommended_threshold, _ = self.recommend_threshold(metrics)
		metrics["recommended_threshold"] = float(recommended_threshold)

		version, artifact_path = self.registry.register(model=model, model_name="rf_anomaly", metrics=metrics)
		self.state_store.save_model_version(
			model_name="rf_anomaly",
			version=version,
			metrics=metrics,
			artifact_path=artifact_path,
		)
		self.state_store.save_training_run(status="success", rows_used=rows_used, metrics=metrics, notes=split_note)

		return TrainingResult(
			success=True,
			rows_used=rows_used,
			metrics=metrics,
			version=version,
			artifact_path=artifact_path,
			notes=split_note,
		)


if __name__ == "__main__":
	trainer = Trainer(load_settings())
	result = trainer.run()
	print(result)
	if result.success:
		recommended_threshold, reason = Trainer.recommend_threshold(result.metrics)
		print(
			f"recommended_threshold={recommended_threshold:.2f} "
			f"reason={reason} "
			f"min_recall_target={Trainer.MIN_RECALL_TARGET:.2f}"
		)

