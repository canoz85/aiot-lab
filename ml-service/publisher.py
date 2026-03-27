from __future__ import annotations

import json

import paho.mqtt.client as mqtt

from config import Settings
from contracts import DecisionEvent


class DecisionPublisher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = mqtt.Client(client_id=f"{settings.mqtt_client_id}-publisher")
        if settings.mqtt_username and settings.mqtt_password:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    def connect(self) -> None:
        self.client.connect(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60)

    def publish(self, event: DecisionEvent) -> None:
        topic = f"{self.settings.decisions_topic_prefix}/{event.device_id}"
        payload = json.dumps(event.to_payload())
        self.client.publish(topic, payload=payload, qos=self.settings.qos, retain=False)
