import logging
import json
import os
from .config import STATE_DIR

log = logging.getLogger(__name__)

STATE_FILE = os.path.join(STATE_DIR, "processed_signals.json")


class Deduplicator:
    def __init__(self):
        self.processed = self._load()

    def _load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def _save(self):
        with open(STATE_FILE, "w") as f:
            json.dump(list(self.processed), f)

    def is_duplicate(self, signal_id):
        return signal_id in self.processed

    def mark_processed(self, signal_id):
        self.processed.add(signal_id)
        self._save()

    def cleanup(self, max_keep=5000):
        if len(self.processed) > max_keep:
            self.processed = set(list(self.processed)[-max_keep:])
            self._save()
