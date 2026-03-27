from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    mqtt_host: str = os.getenv("ML_MQTT_HOST", "localhost")
    mqtt_port: int = int(os.getenv("ML_MQTT_PORT", "1883"))
    mqtt_username: str | None = os.getenv("ML_MQTT_USERNAME")
    mqtt_password: str | None = os.getenv("ML_MQTT_PASSWORD")
    mqtt_client_id: str = os.getenv("ML_MQTT_CLIENT_ID", "ml-service")
    telemetry_topic: str = os.getenv("ML_TELEMETRY_TOPIC", "aiot/telemetry/+")
    decisions_topic_prefix: str = os.getenv("ML_DECISIONS_TOPIC_PREFIX", "aiot/decisions")
    qos: int = int(os.getenv("ML_MQTT_QOS", "1"))

    db_path: Path = Path(os.getenv("ML_DB_PATH", "ml-service/state/ml_service.db"))
    model_dir: Path = Path(os.getenv("ML_MODEL_DIR", "ml-service/models"))
    active_model_file: Path = Path(os.getenv("ML_ACTIVE_MODEL_FILE", "ml-service/models/active_model.joblib"))

    retrain_interval_minutes: int = int(os.getenv("ML_RETRAIN_INTERVAL_MINUTES", "1440"))
    retrain_window_hours: int = int(os.getenv("ML_RETRAIN_WINDOW_HOURS", "168"))
    retrain_min_rows: int = int(os.getenv("ML_RETRAIN_MIN_ROWS", "100"))


def load_settings() -> Settings:
    return Settings()
