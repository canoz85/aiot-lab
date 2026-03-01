from __future__ import annotations

from config import load_settings
from decision_engine import DecisionEngine
from inference import ModelRunner
from ingest import TelemetrySubscriber
from model_registry import ModelRegistry
from publisher import DecisionPublisher
from state_store import StateStore


class MlDecisionService:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.state_store = StateStore(self.settings.db_path)
        self.registry = ModelRegistry(self.settings.model_dir, self.settings.active_model_file)
        self.model_runner = ModelRunner(self.registry)
        self.decision_engine = DecisionEngine(self.model_runner)
        self.publisher = DecisionPublisher(self.settings)
        self.subscriber = TelemetrySubscriber(self.settings, self._process_event)

    def _process_event(self, event) -> None:
        self.state_store.save_telemetry(event)
        decision = self.decision_engine.evaluate(event)
        self.publisher.publish(decision)
        self.state_store.save_decision(decision)

    def run(self) -> None:
        self.publisher.connect()
        self.publisher.client.loop_start()
        try:
            self.subscriber.start()
        except KeyboardInterrupt:
            print("ml-service stopped by user")
        finally:
            self.publisher.client.loop_stop()
            self.publisher.client.disconnect()


if __name__ == "__main__":
    MlDecisionService().run()
