from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib


class ModelRegistry:
    def __init__(self, model_dir: Path, active_model_file: Path):
        self.model_dir = model_dir
        self.active_model_file = active_model_file
        self.metadata_file = self.model_dir / "active_model.json"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.active_model_file.parent.mkdir(parents=True, exist_ok=True)

    def register(self, model: Any, model_name: str, metrics: dict[str, float]) -> tuple[str, str]:
        version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        artifact_name = f"{model_name}_{version}.joblib"
        artifact_path = self.model_dir / artifact_name
        joblib.dump(model, artifact_path)

        joblib.dump(model, self.active_model_file)
        metadata = {
            "model_name": model_name,
            "version": version,
            "artifact_path": str(artifact_path),
            "metrics": metrics,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return version, str(artifact_path)

    def _load_metadata(self) -> dict[str, Any]:
        if not self.metadata_file.exists():
            return {}
        return json.loads(self.metadata_file.read_text(encoding="utf-8"))

    def load_active(self) -> tuple[Any | None, str]:
        if not self.active_model_file.exists():
            return None, "none"

        model = joblib.load(self.active_model_file)
        version = "unknown"
        if self.metadata_file.exists():
            metadata = self._load_metadata()
            version = metadata.get("version", "unknown")
        return model, version

    def load_active_anomaly_threshold(self, default: float = 0.5) -> float:
        metadata = self._load_metadata()
        metrics = metadata.get("metrics", {})
        threshold = metrics.get("recommended_threshold", default)
        try:
            return float(threshold)
        except (TypeError, ValueError):
            return float(default)
