import os
from dotenv import load_dotenv

load_dotenv()

QUANTIVE_API_BASE = os.getenv("QUANTIVE_API_BASE", "https://dash.quantive.my.id")
QUANTIVE_API_KEY = os.getenv("QUANTIVE_API_KEY", "")

EXCHANGE = os.getenv("EXCHANGE", "binance")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_API_SECRET = os.getenv("EXCHANGE_API_SECRET", "")
EXCHANGE_TESTNET = os.getenv("EXCHANGE_TESTNET", "false").lower() == "true"

RISK_PCT_PER_TRADE = float(os.getenv("RISK_PCT_PER_TRADE", "1.0"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "2"))
MAX_SLIPPAGE_PCT = float(os.getenv("MAX_SLIPPAGE_PCT", "0.3"))
ALLOW_SHORT = os.getenv("ALLOW_SHORT", "false").lower() == "true"

QUANTIVE_SUBSCRIPTIONS = os.getenv("QUANTIVE_SUBSCRIPTIONS", "")
QUANTIVE_RISK_CONFIG = os.getenv("QUANTIVE_RISK_CONFIG", "{}")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "2"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ORPHAN_ACTION = os.getenv("ORPHAN_ACTION", "close")

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(STATE_DIR, exist_ok=True)


def get_subscriptions():
    return [s.strip() for s in QUANTIVE_SUBSCRIPTIONS.split(",") if s.strip()]


def get_risk_config():
    import json
    try:
        cfg = json.loads(QUANTIVE_RISK_CONFIG)
    except Exception:
        cfg = {}
    return cfg


def get_risk_for(version_code):
    cfg = get_risk_config()
    vc = cfg.get(version_code, {})
    if isinstance(vc, dict):
        return float(vc.get("risk_pct", vc.get("risk_pct_per_trade", RISK_PCT_PER_TRADE)))
    return RISK_PCT_PER_TRADE


def is_subscribed(version_code):
    return version_code in get_subscriptions()


def validate():
    errors = []
    if not QUANTIVE_API_KEY:
        errors.append("QUANTIVE_API_KEY is not set")
    if not EXCHANGE_API_KEY:
        errors.append("EXCHANGE_API_KEY is not set")
    if not EXCHANGE_API_SECRET:
        errors.append("EXCHANGE_API_SECRET is not set")
    if not get_subscriptions():
        errors.append("QUANTIVE_SUBSCRIPTIONS is empty — no models selected")
    return errors
