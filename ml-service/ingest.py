from __future__ import annotations

import json
from collections.abc import Callable

import paho.mqtt.client as mqtt

from config import Settings
from contracts import TelemetryEvent


def _parse_device_id_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 3:
        return None
    if parts[0] != "aiot" or parts[1] != "telemetry":
        return None
    return parts[2]


def parse_telemetry_message(topic: str, payload_text: str) -> TelemetryEvent:
    payload = json.loads(payload_text)
    if not isinstance(payload, dict):
        raise ValueError("telemetry payload must be a JSON object")

    device_id_topic = _parse_device_id_from_topic(topic)
    if not device_id_topic:
        raise ValueError("invalid topic, expected aiot/telemetry/<device_id>")

    device_id_payload = str(payload.get("device_id", "")).strip()
    if device_id_payload and device_id_payload != device_id_topic:
        raise ValueError("topic device_id does not match payload device_id")

    timestamp = str(payload.get("timestamp", "")).strip()
    fw_version = str(payload.get("fw_version", "unknown")).strip() or "unknown"
    data = payload.get("data", {})
    if not timestamp:
        raise ValueError("missing telemetry timestamp")
    if not isinstance(data, dict):
        raise ValueError("telemetry data must be an object")

    return TelemetryEvent(
        device_id=device_id_topic,
        timestamp=timestamp,
        fw_version=fw_version,
        data=data,
        trace_id=str(payload.get("trace_id", "")).strip() or None,
        raw_topic=topic,
    )


class TelemetrySubscriber:
    def __init__(self, settings: Settings, on_event: Callable[[TelemetryEvent], None]):
        self.settings = settings
        self.on_event = on_event
        self.client = mqtt.Client(client_id=f"{settings.mqtt_client_id}-subscriber")
        if settings.mqtt_username and settings.mqtt_password:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, _rc) -> None:
        client.subscribe(self.settings.telemetry_topic, qos=self.settings.qos)

    def _on_message(self, _client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage) -> None:
        try:
            payload_text = msg.payload.decode("utf-8")
            event = parse_telemetry_message(msg.topic, payload_text)
            self.on_event(event)
        except (ValueError, json.JSONDecodeError):
            return

    def start(self) -> None:
        self.client.connect(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60)
        self.client.loop_forever()
