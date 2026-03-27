from __future__ import annotations

import time

from config import load_settings
from train import Trainer


class RetrainScheduler:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.trainer = Trainer(self.settings)

    def run_forever(self) -> None:
        interval_seconds = max(60, self.settings.retrain_interval_minutes * 60)
        while True:
            self.trainer.run()
            time.sleep(interval_seconds)


if __name__ == "__main__":
    RetrainScheduler().run_forever()
