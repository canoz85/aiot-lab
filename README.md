# AIoT Lab

Minimal local AIoT stack for simulating sensor telemetry, streaming via MQTT, and preparing downstream ML + backend + dashboard integration.

## Architecture Overview

This repository is structured as a modular monorepo with clear service boundaries:

- `sensor-simulator`: Generates and enriches telemetry, then publishes to MQTT.
- `mqtt-broker`: Broker configuration for local MQTT routing.
- `ml-service`: Training, inference, and rule/decision logic.
- `backend-node`: API/metrics bridge for consumers and dashboards.
- `dashboard`: Notes/integration target for ThingsBoard.
- `experiments`: Notebook-based tuning and drift analysis.

## Data Flow (Target)

```text
sensor-simulator
	 |
	 v
 MQTT broker
	 |
	 v
  ml-service
	 |
	 v
decision_engine
	 |
	 v
 backend-node
	 |
	 v
 dashboard (ThingsBoard)
```

## Current Runtime Path (Implemented)

Today, the active path is:

```text
SmartSensor -> FeatureEngine -> MQTTClient -> MQTT topic aiot/telemetry/<device_id>
```

Implemented in:

- `sensor-simulator/simulator.py`: Stateful IoT device + anomaly injection.
- `sensor-simulator/feature_engine.py`: Rolling feature generation (`heat_index`, rolling mean, z-score).
- `sensor-simulator/mqtt_client.py`: MQTT transport abstraction (TCP/WebSocket, optional TLS).
- `sensor-simulator/app.py`: Main loop orchestration and publish.

## Component Status

| Component | Purpose | Status |
|---|---|---|
| `sensor-simulator` | Generate + enrich telemetry and publish to MQTT | Implemented |
| `mqtt-broker` | Local broker configuration | Implemented |
| `ml-service` | Train/infer/decision services | Implemented |
| `backend-node` | API and metrics bridge | Implemented |
| `dashboard` | ThingsBoard integration notes | Scaffolded (notes file empty) |
| `experiments` | ML experimentation notebooks | Present |

## ml-service Implementation (Current)

The `ml-service` now includes both online decisioning and offline retraining paths.

### Module Structure

- `ml-service/service.py`: Online runtime entrypoint (subscribe -> evaluate -> publish).
- `ml-service/ingest.py`: MQTT subscriber for `aiot/telemetry/+` with payload/topic validation.
- `ml-service/decision_engine.py`: Rule-based and fused decision policy.
- `ml-service/inference.py`: Model loading and inference fallback behavior.
- `ml-service/publisher.py`: Decision publisher to `aiot/decisions/<device_id>`.
- `ml-service/state_store.py`: SQLite state for telemetry, decisions, training runs, model versions.
- `ml-service/model_registry.py`: Versioned model artifacts and active model promotion.
- `ml-service/train.py`: Historical-data trainer.
- `ml-service/retrain_scheduler.py`: Scheduled retraining loop.
- `ml-service/config.py`: Environment-driven runtime settings.
- `ml-service/contracts.py`: Interface dataclasses for telemetry, rule/model results, decisions.

### Runtime Commands

From `ml-service/`:

```bash
pip install -r requirements.txt
python service.py
```

Run scheduled retraining worker:

```bash
python retrain_scheduler.py
```

## backend-node Implementation (Current)

`backend-node` subscribes to ML decisions and exposes minimal query APIs.

### Topic Contract

- Subscribes to: `aiot/decisions/+`
- Validates topic shape and `device_id` consistency.
- Stores latest decision per device plus bounded recent history in memory.

### API Endpoints

- `GET /health`: process and ingestion counters.
- `GET /decisions/latest`: map of latest decision by `device_id`.
- `GET /decisions/recent?limit=50`: newest decisions first.
- `GET /decisions/:deviceId`: latest decision for one device.

### Runtime Commands

From `backend-node/`:

```bash
npm install
npm start
```

## mqtt-broker Implementation (Current)

`mqtt-broker` is now runnable locally via Docker Compose using Mosquitto.

### Runtime Commands

From repository root:

```bash
docker compose up -d mqtt-broker
docker compose logs -f mqtt-broker
```

### Local End-to-End Start Order

1. Start broker:

```bash
docker compose up -d mqtt-broker
```

2. Start `backend-node`:

```bash
cd backend-node
npm start
```

3. Start `ml-service`:

```bash
cd ml-service
python service.py
```

4. Start `sensor-simulator`:

```bash
cd sensor-simulator
python app.py
```

## Telemetry Shape

Each message follows a packet-style structure with metadata and nested sensor payload:

```text
{
  "device_id": "AIoT_Edge_01",
  "timestamp": "...",
  "fw_version": "1.0.2",
  "data": {
    "temperature": ...,
    "humidity": ...,
    "motion": ...,
    "light_lux": ...,
    "heat_index": ...,          # added by feature engine
    "temp_rolling_mean": ...,   # added when history is available
    "temp_z_score": ...         # added when history is available
  }
}
```

## Repo Layout

```text
aiot-lab/
├─ sensor-simulator/
├─ mqtt-broker/
├─ ml-service/
├─ backend-node/
├─ dashboard/
└─ experiments/
```
