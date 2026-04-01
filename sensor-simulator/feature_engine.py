from collections import deque

import numpy as np


class FeatureEngine:
    # Smoothing factor for exponential moving average (0 < alpha <= 1).
    # 0.3 is a common default: it weights the last ~3–4 readings most heavily
    # while still keeping a memory of earlier values.  Increase toward 1.0 for
    # faster reaction to spikes; decrease toward 0.0 for a smoother trend line.
    EMA_ALPHA = 0.3

    def __init__(self, window_size=10):
        self.history = deque(maxlen=window_size)

    def process(self, full_packet):
        # 1. Access the telemetry part
        telemetry = full_packet["data"]
        current_temp = telemetry["temperature"]

        # 2. Derived feature: heat index (always available)
        telemetry["heat_index"] = round(current_temp + 0.1 * telemetry["humidity"], 2)

        # 3. Temporal features — require at least one previous reading in the
        #    rolling window.  On the very first reading all of these are absent
        #    from the dict; callers that need a numeric default use 0.0.
        if self.history:
            prev = self.history[-1]
            prev_temp = prev["temperature"]
            temps = [d["temperature"] for d in self.history]
            avg_temp = float(np.mean(temps))
            std_temp = float(np.std(temps))

            # Rolling mean — centre of the recent distribution
            telemetry["temp_rolling_mean"] = round(avg_temp, 2)

            # Rolling std — how volatile the temperature has been.
            # 3 dp used for computed statistics to preserve meaningful precision.
            telemetry["temp_rolling_std"] = round(std_temp, 3)

            # Z-score — how many std deviations the current reading sits from
            #            the rolling mean (safe division: flat windows → 0)
            telemetry["temp_z_score"] = (
                round((current_temp - avg_temp) / std_temp, 2)
                if std_temp > 0.001
                else 0.0
            )

            # Delta — rate of change from the immediately previous reading.
            # A sudden large delta is a strong anomaly signal even when the
            # absolute temperature looks normal.
            telemetry["temp_delta"] = round(current_temp - prev_temp, 3)

            # Lag-1 — the raw previous temperature value.
            # Gives the model a direct "what was it just before?" input.
            telemetry["temp_lag_1"] = round(prev_temp, 3)

            # EMA — exponentially weighted moving average.
            # Smooths noise while staying responsive to genuine trends.
            # Cold-start seed: on the very first history entry temp_ema is not
            # yet present, so we fall back to prev_temp — equivalent to
            # initialising the EMA at the first observed value, which is the
            # standard convention.
            prev_ema = prev.get("temp_ema", prev_temp)
            telemetry["temp_ema"] = round(
                self.EMA_ALPHA * current_temp + (1 - self.EMA_ALPHA) * prev_ema, 3
            )

        # 4. Update history with a COPY of the telemetry
        self.history.append(telemetry.copy())

        # 5. Return the WHOLE packet (device_id is still there)
        return full_packet