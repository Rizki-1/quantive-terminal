import time
import requests
import logging
from .config import QUANTIVE_API_BASE, QUANTIVE_API_KEY, get_subscriptions

log = logging.getLogger(__name__)


class SignalClient:
    def __init__(self):
        self.base = QUANTIVE_API_BASE.rstrip("/")
        self.api_key = QUANTIVE_API_KEY
        self.last_since = None
        self.session = requests.Session()
        self.session.headers.update({
            "X-Quantive-Key": self.api_key,
            "User-Agent": "quantive-terminal/0.1.0",
        })

    def _get(self, path, params=None):
        url = f"{self.base}{path}"
        try:
            r = self.session.get(url, params=params, timeout=10)
            if r.status_code == 401:
                log.error("API key invalid or expired")
                return None
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            log.error(f"API request failed: {e}")
            return None

    def health(self):
        return self._get("/api/v1/health")

    def validate_api_key(self):
        data = self._get("/api/v1/auth/me")
        if data:
            subs = [s["version_code"] for s in data.get("subscriptions", [])]
            return True, subs
        return False, []

    def get_subscriptions(self):
        data = self._get("/api/v1/auth/me")
        if data:
            subs = [s["version_code"] for s in data.get("subscriptions", [])]
            return subs
        return get_subscriptions()

    def get_versions(self):
        return self._get("/api/v1/versions") or []

    def poll_signals(self, since=None):
        params = {}
        if since or self.last_since:
            params["since"] = since or self.last_since
        data = self._get("/api/v1/signals/latest", params)
        if data:
            if isinstance(data, list) and data:
                self.last_since = max(
                    s.get("issued_at", "") for s in data if "issued_at" in s
                )
        return data or []

    def get_balance_hint(self):
        profile = self._get("/api/v1/auth/me")
        if profile and profile.get("exchange"):
            return profile["exchange"]
        return None
