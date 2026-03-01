const express = require("express");
const mqtt = require("mqtt");

const { createMetrics, recordDecision, recordInvalid } = require("./metrics");

const PORT = Number(process.env.PORT || 3001);
const MQTT_HOST = process.env.MQTT_HOST || "localhost";
const MQTT_PORT = Number(process.env.MQTT_PORT || 1883);
const MQTT_URL = process.env.MQTT_URL || `mqtt://${MQTT_HOST}:${MQTT_PORT}`;
const MQTT_TOPIC = process.env.MQTT_DECISIONS_TOPIC || "aiot/decisions/+";
const MAX_RECENT = Number(process.env.MAX_RECENT_DECISIONS || 500);

const app = express();
const metrics = createMetrics();

const latestByDevice = new Map();
const recentDecisions = [];

function parseDeviceId(topic) {
	const parts = String(topic || "").split("/");
	if (parts.length !== 3) {
		return null;
	}
	if (parts[0] !== "aiot" || parts[1] !== "decisions") {
		return null;
	}
	return parts[2];
}

function storeDecision(payload) {
	latestByDevice.set(payload.device_id, payload);
	recentDecisions.push(payload);
	if (recentDecisions.length > MAX_RECENT) {
		recentDecisions.shift();
	}
}

const mqttClient = mqtt.connect(MQTT_URL);

mqttClient.on("connect", () => {
	mqttClient.subscribe(MQTT_TOPIC, { qos: 1 }, (err) => {
		if (err) {
			console.error("Failed to subscribe decisions topic", err.message);
			return;
		}
		console.log(`Subscribed to ${MQTT_TOPIC}`);
	});
});

mqttClient.on("message", (topic, messageBuffer) => {
	try {
		const deviceIdFromTopic = parseDeviceId(topic);
		if (!deviceIdFromTopic) {
			recordInvalid(metrics);
			return;
		}

		const payload = JSON.parse(messageBuffer.toString("utf8"));
		if (!payload || typeof payload !== "object") {
			recordInvalid(metrics);
			return;
		}

		if (!payload.device_id) {
			payload.device_id = deviceIdFromTopic;
		}

		if (payload.device_id !== deviceIdFromTopic) {
			recordInvalid(metrics);
			return;
		}

		if (!payload.timestamp) {
			recordInvalid(metrics);
			return;
		}

		storeDecision(payload);
		recordDecision(metrics);
	} catch (error) {
		recordInvalid(metrics);
	}
});

mqttClient.on("error", (error) => {
	console.error("MQTT error", error.message);
});

app.get("/health", (_req, res) => {
	res.json({
		status: "ok",
		mqttConnected: mqttClient.connected,
		...metrics,
	});
});

app.get("/decisions/latest", (_req, res) => {
	res.json(Object.fromEntries(latestByDevice.entries()));
});

app.get("/decisions/recent", (req, res) => {
	const limit = Math.max(1, Math.min(Number(req.query.limit || 50), MAX_RECENT));
	const items = recentDecisions.slice(-limit).reverse();
	res.json(items);
});

app.get("/decisions/:deviceId", (req, res) => {
	const decision = latestByDevice.get(req.params.deviceId);
	if (!decision) {
		res.status(404).json({ error: "device decision not found" });
		return;
	}
	res.json(decision);
});

app.listen(PORT, () => {
	console.log(`backend-node listening on port ${PORT}`);
});

