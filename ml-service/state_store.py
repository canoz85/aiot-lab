from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from contracts import DecisionEvent, TelemetryEvent


class StateStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS telemetry_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    fw_version TEXT,
                    trace_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(device_id, timestamp, trace_id)
                );

                CREATE TABLE IF NOT EXISTS decision_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    correlation_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    metrics_json TEXT,
                    artifact_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(model_name, version)
                );

                CREATE TABLE IF NOT EXISTS training_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rows_used INTEGER NOT NULL,
                    metrics_json TEXT,
                    notes TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_telemetry_device_ts
                    ON telemetry_history(device_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_decision_device_ts
                    ON decision_history(device_id, timestamp);
                """
            )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_telemetry(self, event: TelemetryEvent) -> None:
        payload_json = json.dumps(
            {
                "device_id": event.device_id,
                "timestamp": event.timestamp,
                "fw_version": event.fw_version,
                "data": event.data,
                "trace_id": event.trace_id,
                "raw_topic": event.raw_topic,
            },
            separators=(",", ":"),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO telemetry_history
                (device_id, timestamp, fw_version, trace_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.device_id,
                    event.timestamp,
                    event.fw_version,
                    event.trace_id or "",
                    payload_json,
                    self._utc_now(),
                ),
            )

    def save_decision(self, event: DecisionEvent) -> None:
        payload_json = json.dumps(event.to_payload(), separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO decision_history
                (device_id, timestamp, decision, severity, correlation_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.device_id,
                    event.timestamp,
                    event.decision,
                    event.severity,
                    event.correlation_id,
                    payload_json,
                    self._utc_now(),
                ),
            )

    def fetch_telemetry_window(self, hours: int) -> list[dict[str, Any]]:
        min_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM telemetry_history
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (min_time,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_model_version(
        self,
        model_name: str,
        version: str,
        metrics: dict[str, float],
        artifact_path: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO model_versions
                (model_name, version, metrics_json, artifact_path, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    model_name,
                    version,
                    json.dumps(metrics, separators=(",", ":")),
                    artifact_path,
                    self._utc_now(),
                ),
            )

    def save_training_run(
        self,
        status: str,
        rows_used: int,
        metrics: dict[str, float] | None = None,
        notes: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO training_runs
                (run_at, status, rows_used, metrics_json, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self._utc_now(),
                    status,
                    rows_used,
                    json.dumps(metrics or {}, separators=(",", ":")),
                    notes,
                ),
            )
