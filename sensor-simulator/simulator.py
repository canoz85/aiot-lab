import random
import time
from datetime import datetime

class IoTDevice:
    """Base class for all IoT hardware types."""
    def __init__(self, device_id, firmware="1.0.2"):
        self.device_id = device_id
        self.firmware = firmware

    def get_context(self):
        """Returns standard metadata for every message."""
        return {
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "fw_version": self.firmware
        }

class SmartSensor(IoTDevice):
    """Specific sensor implementation with internal state and logic."""
    def __init__(self, device_id):
        super().__init__(device_id)
        # Initial states for temporal consistency (Random Walk)
        self.temp = 22.0
        self.hum = 55.0

    def _apply_physics(self):
        """Simulates real-world correlations and trends."""
        # 1. Temporal Drift (Current value depends on previous)
        self.temp += random.normalvariate(0, 0.1)
        self.hum += random.normalvariate(0, 0.2)
        
        # 2. Logic: Motion-Light Correlation
        is_motion = random.random() < 0.1
        light = random.uniform(600, 900) if is_motion else random.uniform(20, 150)
        
        return is_motion, round(light, 2)

    def produce_data(self):
        """Generates the final AI-ready payload."""
        motion, light = self._apply_physics()
        
        # 3. Anomaly Injection (1% chance for AI to detect later)
        temp_outlier = self.temp + 20.0 if random.random() < 0.01 else self.temp

        # Merge Base Metadata + Telemetry
        payload = self.get_context()
        payload["data"] = {
            "temperature": round(temp_outlier, 2),
            "humidity": round(self.hum, 2),
            "motion": motion,
            "light_lux": light
        }
        return payload

# # --- Execution Logic ---
# if __name__ == "__main__":
#     # Create an instance (The Object)
#     sensor_node = SmartSensor("AIOT_01")

#     print(f"Node {sensor_node.device_id} is active...")
#     try:
#         while True:
#             data = sensor_node.produce_data()
#             print(f"DATA: {data}")
#             time.sleep(2)
#     except KeyboardInterrupt:
#         print("Simulation stopped.")