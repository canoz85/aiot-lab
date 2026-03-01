import time
import uuid

from simulator import SmartSensor
from feature_engine import FeatureEngine
from mqtt_client import MQTTClient

# DEVICE_ID = str(uuid.uuid4())[:8]

engine = FeatureEngine(window_size=10)
mqtt = MQTTClient("mqtt-dashboard.com", 8884, "aiot/sensors/telemetry/xx", use_tls=True,
    use_websocket=True,)
mqtt.connect()

 # Create an instance (The Object)
sensor_node = SmartSensor("AIoT_Edge_01")

print(f"Node {sensor_node.device_id} is active...")

try:
    while True:
     # Generate stateful payload
        raw_payload = sensor_node.produce_data()
        # print(f"DATA: {data}")
        
        enriched_payload = engine.process(raw_payload)

        topic = f"aiot/telemetry/{enriched_payload['device_id']}"
        status = mqtt.publish(enriched_payload, topic=topic)

        if status == 0:
            print(f"[SENT] Topic: {topic} | Temp: {enriched_payload['data']['temperature']}")
        else:
            print(f"[ERROR] Failed to publish message")

        time.sleep(1)
except KeyboardInterrupt:
    print("\nSimulation terminated by user.")

