import sys
import time
import logging
from .signal_client import SignalClient
from .exchanges.binance import BinanceExchange
from .exchanges.bybit import BybitExchange
from .notifier import Notifier
from .fingerprint import get_fingerprint
from . import config

log = logging.getLogger(__name__)


def _get_exchange():
    name = config.EXCHANGE.lower()
    if name == "binance":
        return BinanceExchange(config.EXCHANGE_API_KEY, config.EXCHANGE_API_SECRET, config.EXCHANGE_TESTNET)
    elif name == "bybit":
        return BybitExchange(config.EXCHANGE_API_KEY, config.EXCHANGE_API_SECRET, config.EXCHANGE_TESTNET)
    else:
        raise ValueError(f"Unsupported exchange: {name}")


def run_connect_test():
    errors = []
    print("=" * 50)
    print("  Quantive Terminal — Connection Test")
    print("=" * 50)

    print(f"\n  Server fingerprint: {get_fingerprint()[:16]}...")

    print(f"\n[1] Quantive API ({config.QUANTIVE_API_BASE})")
    try:
        client = SignalClient()
        health = client.health()
        if health and health.get("status") == "ok":
            print(f"  [OK] Connected")
        else:
            print(f"  [FAIL] Health check failed: {health}")
            errors.append("API health check failed")
    except Exception as e:
        print(f"  [FAIL] Connection failed: {e}")
        errors.append("API connection")

    print(f"\n[2] API Key")
    try:
        subs = client.get_subscriptions()
        if subs is None:
            print(f"  [FAIL] API key invalid")
            errors.append("API key")
        else:
            print(f"  [OK] API key valid — {len(subs)} subscription(s)")
    except Exception as e:
        print(f"  [FAIL] API key check failed: {e}")
        errors.append("API key")

    print(f"\n[3] Exchange ({config.EXCHANGE.upper()})")
    try:
        exchange = _get_exchange()
        balance = exchange.fetch_balance()
        if balance > 0:
            print(f"  [OK] Connected — Balance: {balance:.2f} USDT")
        else:
            print(f"  [FAIL] Balance zero or fetch failed")
            errors.append("Exchange balance")
    except Exception as e:
        print(f"  [FAIL] Exchange connection failed: {e}")
        errors.append("Exchange connection")

    print(f"\n[4] Telegram Notifications")
    try:
        notifier = Notifier()
        if notifier.enabled:
            ok = notifier.send_test()
            if ok:
                print(f"  [OK] Test message sent")
            else:
                print(f"  [FAIL] Telegram not configured (optional)")
        else:
            print(f"  - Not configured (optional)")
    except Exception as e:
        print(f"  [FAIL] Telegram failed: {e}")

    print(f"\n[5] Subscriptions")
    for vc in config.get_subscriptions():
        print(f"  • {vc} (risk: {config.get_risk_for(vc)}%)")

    validation = config.validate()
    if validation:
        print(f"\n  WARN Config warnings:")
        for w in validation:
            print(f"    - {w}")

    if errors:
        print(f"\n  [FAIL] {len(errors)} error(s) found. Fix before running.")
        return False
    else:
        print(f"\n  [OK] All checks passed. Ready to run.")
        return True
