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
| `mqtt-broker` | Local broker configuration | Scaffolded (config file empty) |
| `ml-service` | Train/infer/decision services | Scaffolded (core files empty) |
| `backend-node` | API and metrics bridge | Scaffolded (core files empty) |
| `dashboard` | ThingsBoard integration notes | Scaffolded (notes file empty) |
| `experiments` | ML experimentation notebooks | Present |

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
