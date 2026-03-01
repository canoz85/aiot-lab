from collections import deque

import numpy as np


class FeatureEngine:
    def __init__(self, window_size=10):
        self.history = deque(maxlen=window_size)

    def process(self, full_packet):
        # 1. Access the telemetry part
        telemetry = full_packet["data"]
        
        # 2. Perform calculations on telemetry
        # (Your existing logic here...)
        telemetry["heat_index"] = round(telemetry["temperature"] + 0.1 * telemetry["humidity"], 2)
        
        # 3. Handle numpy types and Z-score safely
        temps = [d["temperature"] for d in self.history]
        if temps:
            avg_temp = float(np.mean(temps))
            std_temp = float(np.std(temps))
            
            telemetry["temp_rolling_mean"] = round(avg_temp, 2)
            # Safe division for Z-Score
            if std_temp > 0.001:
                telemetry["temp_z_score"] = round((telemetry["temperature"] - avg_temp) / std_temp, 2)
            else:
                telemetry["temp_z_score"] = 0.0
        
        # 4. Update history with a COPY of the telemetry
        self.history.append(telemetry.copy())
        
        # 5. Return the WHOLE packet (device_id is still there)
        return full_packet