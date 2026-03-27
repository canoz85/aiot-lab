import time
import os

from mqtt_client import MQTTClient
from feature_engine import FeatureEngine
from simulator import SmartSensor

def main():
    engine = FeatureEngine(window_size=10)
    mqtt = MQTTClient(
        host=os.getenv("SIM_MQTT_HOST", "localhost"),
        port=int(os.getenv("SIM_MQTT_PORT", "1883")),
        topic=None,
        use_tls=False,
        use_websocket=False,
    )
    mqtt.connect()

    sensor_node = SmartSensor("AIoT_Edge_01")

    print(f"Node {sensor_node.device_id} is active...")

    try:
        while True:
            # Generate stateful payload
            raw_payload = sensor_node.produce_data()
            enriched_payload = engine.process(raw_payload)

            topic = f"aiot/telemetry/{enriched_payload['device_id']}"
            status = mqtt.publish(enriched_payload, topic=topic)

            if status == 0:
                print(f"[SENT] Topic: {topic} | Temp: {enriched_payload['data']['temperature']}")
            else:
                print("[ERROR] Failed to publish message")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulation terminated by user.")
    finally:
        mqtt.disconnect()


if __name__ == "__main__":
    main()

