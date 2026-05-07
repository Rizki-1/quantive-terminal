import requests
import logging
from . import config

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class Notifier:
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

    def _send(self, text):
        if not self.enabled:
            return
        try:
            url = f"{TELEGRAM_API}/bot{self.token}/sendMessage"
            requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
            }, timeout=5)
        except Exception as e:
            log.error(f"Telegram send failed: {e}")

    def send_trade_open(self, signal, entry_price, size):
        version = signal.get("version_code", "")
        side = signal.get("side", "LONG")
        emoji = "🟢" if side.upper() == "LONG" else "🔴"
        msg = (
            f"{emoji} <b>{side} OPEN</b>\n"
            f"Version: {version}\n"
            f"Entry: {entry_price}\n"
            f"Size: {size:.4f}\n"
            f"TP: {signal.get('tp', [{}])[0].get('value', 'N/A') if signal.get('tp') else 'N/A'}\n"
            f"SL: {signal.get('sl', {}).get('value', 'N/A')}"
        )
        self._send(msg)

    def send_trade_close(self, signal, exit_price):
        version = signal.get("version_code", "")
        side = signal.get("side", "LONG")
        msg = (
            f"⏹ <b>{side} CLOSE</b>\n"
            f"Version: {version}\n"
            f"Exit: {exit_price}"
        )
        self._send(msg)

    def send_test(self):
        self._send("Quantive Terminal: Test message. Notifications working.")
        return self.enabled

    def send_error(self, text):
        self._send(f"⚠ <b>Error</b>\n{text}")
