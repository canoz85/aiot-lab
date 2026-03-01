## Plan: Understand AIoT Lab End-to-End (DRAFT)

Start from the system boundary (broker + topics + API contract), then go into the ML service online path, then model lifecycle/retraining, and finally revisit the simulator internals you already know. This order reduces cognitive load because each deeper module is anchored to an already-understood input/output contract. I’m assuming your goal is architecture comprehension (not immediate refactoring), so the plan focuses on reading order, what to extract from each file, and quick validation checks at each stage.

**Steps**
1. Read [README.md](README.md) once to map components, topic names, and startup order; write down the three critical MQTT topics and two API endpoints as your anchor artifacts.
2. Inspect infrastructure boundaries in [docker-compose.yml](docker-compose.yml) and [mqtt-broker/mosquitto.conf](mqtt-broker/mosquitto.conf) to understand broker port/auth assumptions before diving into service code.
3. Learn consumer contract from [backend-node/server.js](backend-node/server.js) and [backend-node/metrics.js](backend-node/metrics.js): trace how decision payloads are validated, stored in-memory, and exposed through HTTP.
4. Build ML mental model from config/contracts first: [ml-service/config.py](ml-service/config.py) then [ml-service/contracts.py](ml-service/contracts.py); note `Settings`, `TelemetryEvent`, `DecisionEvent`, and required payload fields.
5. Follow online inference pipeline in strict order: [ml-service/ingest.py](ml-service/ingest.py) → [ml-service/inference.py](ml-service/inference.py) → [ml-service/decision_engine.py](ml-service/decision_engine.py) → [ml-service/publisher.py](ml-service/publisher.py) → [ml-service/service.py](ml-service/service.py); for each hop, record input schema, transformation, output schema.
6. Understand persistence and model lifecycle: [ml-service/state_store.py](ml-service/state_store.py), [ml-service/model_registry.py](ml-service/model_registry.py), [ml-service/train.py](ml-service/train.py), [ml-service/retrain_scheduler.py](ml-service/retrain_scheduler.py); trace where telemetry history becomes labels/features and how active model versions are switched.
7. Revisit simulator with pipeline context: [sensor-simulator/app.py](sensor-simulator/app.py), [sensor-simulator/simulator.py](sensor-simulator/simulator.py), [sensor-simulator/feature_engine.py](sensor-simulator/feature_engine.py), [sensor-simulator/mqtt_client.py](sensor-simulator/mqtt_client.py); confirm exactly which simulated fields are consumed by ML rules/model.
8. Check project completeness/status artifacts: [dashboard/thingsboard-notes.md](dashboard/thingsboard-notes.md), [experiments/drift_detection.ipynb](experiments/drift_detection.ipynb), [experiments/threshold_tuning.ipynb](experiments/threshold_tuning.ipynb), [notes.txt](notes.txt); treat them as roadmap notes unless backed by runnable code.

**Verification**
- Run and observe message flow in this order: broker → backend → ML service → simulator; verify decisions appear at backend endpoints after telemetry starts.
- Manually verify one full device trace: telemetry publish → ML decision publish → backend latest/recent update.
- Confirm retraining path by triggering scheduler/trainer once and checking model metadata/state updates in SQLite/model directory.

**Decisions**
- Chose “outside-in” learning over per-folder reading because message contracts explain module intent faster.
- Prioritized [backend-node/server.js](backend-node/server.js) before ML internals so decision output requirements are clear first.
- Treated dashboard/experiments as non-authoritative because they are currently placeholders/empty.
