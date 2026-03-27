from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TelemetryEvent:
    device_id: str
    timestamp: str
    fw_version: str
    data: dict[str, Any]
    trace_id: str | None = None
    raw_topic: str | None = None


@dataclass(slots=True)
class RuleResult:
    triggered_rules: list[str] = field(default_factory=list)
    severity: str = "info"
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ModelResult:
    model_version: str = "none"
    score: float = 0.0
    label: str = "normal"
    confidence: float = 0.0


@dataclass(slots=True)
class DecisionEvent:
    device_id: str
    timestamp: str
    decision: str
    severity: str
    reason_codes: list[str]
    rule_result: RuleResult
    model_result: ModelResult
    correlation_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["published_at"] = utc_now_iso()
        return payload


@dataclass(slots=True)
class ModelMetadata:
    model_name: str
    version: str
    trained_at: str
    feature_names: list[str]
    metrics: dict[str, float] = field(default_factory=dict)
    artifact_path: str = ""
