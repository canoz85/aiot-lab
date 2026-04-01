from __future__ import annotations

from contracts import DecisionEvent, ModelResult, RuleResult, TelemetryEvent
from inference import ModelRunner


class RuleEngine:
	def evaluate(self, event: TelemetryEvent) -> RuleResult:
		data = event.data
		triggered_rules: list[str] = []
		reasons: list[str] = []
		severity = "info"

		temp = float(data.get("temperature", 0.0))
		humidity = float(data.get("humidity", 0.0))
		z_score = float(data.get("temp_z_score", 0.0))

		if temp > 45.0:
			triggered_rules.append("TEMP_CRITICAL_HIGH")
			reasons.append("temperature_above_45")
			severity = "critical"
		elif temp > 35.0:
			triggered_rules.append("TEMP_WARN_HIGH")
			reasons.append("temperature_above_35")
			severity = "warning"

		if humidity < 20.0:
			triggered_rules.append("HUMIDITY_LOW")
			reasons.append("humidity_below_20")
			if severity == "info":
				severity = "warning"

		if abs(z_score) >= 3.0:
			triggered_rules.append("TEMP_ZSCORE_OUTLIER")
			reasons.append("z_score_abs_ge_3")
			if severity == "info":
				severity = "warning"

		return RuleResult(triggered_rules=triggered_rules, severity=severity, reasons=reasons)


class DecisionEngine:
	def __init__(self, model_runner: ModelRunner):
		self.rule_engine = RuleEngine()
		self.model_runner = model_runner

	def evaluate(self, event: TelemetryEvent) -> DecisionEvent:
		rule_result = self.rule_engine.evaluate(event)
		model_result = self.model_runner.predict(event.data)

		decision = "allow"
		severity = "info"
		reason_codes: list[str] = []

		if rule_result.severity == "critical":
			decision = "alert"
			severity = "critical"
			reason_codes.extend(rule_result.triggered_rules)
		elif rule_result.triggered_rules:
			decision = "review"
			severity = "warning"
			reason_codes.extend(rule_result.triggered_rules)

		if model_result.label == "anomaly" and model_result.score >= self.model_runner.anomaly_threshold:
			if decision == "allow":
				decision = "review"
				severity = "warning"
			reason_codes.append("MODEL_ANOMALY_HIGH")

		if not reason_codes:
			reason_codes.append("NO_ALERT_CONDITIONS")

		return DecisionEvent(
			device_id=event.device_id,
			timestamp=event.timestamp,
			decision=decision,
			severity=severity,
			reason_codes=reason_codes,
			rule_result=rule_result,
			model_result=model_result,
			correlation_id=event.trace_id,
		)

