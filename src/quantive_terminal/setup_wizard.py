import os
import re
import requests
import json
import sys
import socket
from .fingerprint import get_fingerprint

CONFIG_FILE = ".env"
API_BASE = "https://dash.quantive.my.id"


def print_header(text):
    print(f"\n{'='*55}")
    print(f"  {text}")
    print(f"{'='*55}")


def input_required(prompt, default=None):
    while True:
        d = f" [{default}]" if default else ""
        val = input(f"  {prompt}{d}: ").strip()
        if val:
            return val
        if default:
            return default


def input_choice(prompt, options):
    print(f"  {prompt}")
    for i, (label, desc) in enumerate(options, 1):
        print(f"    [{i}] {label}  — {desc}")
    while True:
        try:
            choice = input("  > ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            pass
        print("  Invalid choice, try again")


def input_yesno(prompt, default="n"):
    d = "Y/n" if default == "y" else "y/N"
    val = input(f"  {prompt} [{d}]: ").strip().lower()
    if not val:
        return default == "y"
    return val.startswith("y")


def run_setup():
    config = {}
    print_header("QUANTIVE TERMINAL — SETUP WIZARD")

    # Step 1: License
    print_header("[1/5] LICENSE")
    print("  [1] Activate with license key")
    print("  [2] Start FREE TRIAL (3 days, 1 model)")
    choice = input("  > ").strip()

    email = input_required("Enter your email")
    fingerprint = get_fingerprint()

    if choice == "2":
        print("  Starting free trial...")
        try:
            r = requests.post(f"{API_BASE}/api/v1/license/activate", json={
                "trial": True, "email": email,
                "fingerprint": fingerprint,
                "hostname": socket.gethostname(),
            }, timeout=10)
            data = r.json()
            if data.get("success"):
                config["QUANTIVE_API_KEY"] = data["api_key"]
                print(f"  Trial activated! {data.get('days_remaining', 3)} days remaining")
                print(f"  Tier: {data.get('tier', 'trial')}")
            else:
                print(f"  [FAIL] Trial failed: {data.get('message', 'Unknown error')}")
                if input_yesno("Retry with license key?", "y"):
                    choice = "1"
                else:
                    sys.exit(1)
        except Exception as e:
            print(f"  [FAIL] Connection failed: {e}")
            sys.exit(1)

    if choice == "1":
        license_key = input_required("Enter license key")
        print("  Verifying license...")
        try:
            r = requests.post(f"{API_BASE}/api/v1/license/activate", json={
                "license_key": license_key, "email": email,
                "fingerprint": fingerprint,
                "hostname": socket.gethostname(),
            }, timeout=10)
            data = r.json()
            if data.get("success"):
                config["QUANTIVE_API_KEY"] = data["api_key"]
                print(f"  License activated!")
                print(f"  Tier: {data.get('tier', 'pro')}")
                if data.get("expires_at"):
                    print(f"  Expires: {data['expires_at'][:10]}")
            else:
                print(f"  [FAIL] Activation failed: {data.get('message', 'Unknown error')}")
                sys.exit(1)
        except Exception as e:
            print(f"  [FAIL] Connection failed: {e}")
            sys.exit(1)

    # Step 2: Exchange
    print_header("[2/5] EXCHANGE")
    exchange = input_choice("Select exchange:", [
        ("binance", "Binance Futures"),
        ("bybit", "Bybit Perpetuals"),
        ("lighter", "Lighter DEX"),
    ])
    config["EXCHANGE"] = exchange
    config["EXCHANGE_API_KEY"] = input_required("Enter API Key")
    config["EXCHANGE_API_SECRET"] = input_required("Enter API Secret")
    config["EXCHANGE_TESTNET"] = "true" if input_yesno("Use testnet?", "n") else "false"

    # Step 3: Telegram
    print_header("[3/5] TELEGRAM NOTIFICATIONS (Optional)")
    bot_token = input("  Bot Token (Enter to skip): ").strip()
    if bot_token:
        chat_id = input_required("Chat ID")
        config["TELEGRAM_BOT_TOKEN"] = bot_token
        config["TELEGRAM_CHAT_ID"] = chat_id
        print("  Telegram configured")
    else:
        print("  Skipped")

    # Step 4: Model selection
    print_header("[4/5] MODEL SELECTION")
    print("  Fetching available versions...")
    try:
        headers = {"X-Quantive-Key": config["QUANTIVE_API_KEY"]}
        r = requests.get(f"{API_BASE}/api/v1/versions", headers=headers, timeout=10)
        versions = r.json() if r.ok else []
    except Exception:
        versions = []

    if not versions:
        versions = [
            {"version_code": "BTC_1H_ML_V1", "display_name": "BTC V1 — ML HHHL (RR 1:1)", "asset": "BTC", "tp_pct": 3.0, "sl_pct": 3.0, "rr": "1:1", "tier_required": "free"},
            {"version_code": "BTC_1H_ML_V2", "display_name": "BTC V2 — Pivot Filter (RR 1:1)", "asset": "BTC", "tp_pct": 3.0, "sl_pct": 3.0, "rr": "1:1", "tier_required": "pro"},
            {"version_code": "BTC_1H_ML_V3", "display_name": "BTC V3 — Dow Theory LONG (RR 1:1)", "asset": "BTC", "tp_pct": 3.0, "sl_pct": 3.0, "rr": "1:1", "tier_required": "pro"},
            {"version_code": "BTC_1H_ML_V3_RR2","display_name": "BTC V3 — Dow Theory RR 1:2", "asset": "BTC", "tp_pct": 3.0, "sl_pct": 1.5, "rr": "1:2", "tier_required": "vip"},
            {"version_code": "ETH_1H_ML_V1", "display_name": "ETH V1 — ML HHHL (RR 1:1)", "asset": "ETH", "tp_pct": 3.0, "sl_pct": 3.0, "rr": "1:1", "tier_required": "free"},
            {"version_code": "ETH_1H_ML_V2", "display_name": "ETH V2 — Pivot Filter (RR 1:1)", "asset": "ETH", "tp_pct": 3.0, "sl_pct": 3.0, "rr": "1:1", "tier_required": "pro"},
        ]

    print(f"  {'#':2s} {'Model':40s} {'TP':6s} {'SL':6s} {'RR':5s} {'Tier'}")
    print(f"  {'-'*2} {'-'*40} {'-'*6} {'-'*6} {'-'*5} {'-'*6}")
    for i, v in enumerate(versions, 1):
        print(f"  {i:2d} {v['display_name']:40s} {v['tp_pct']}%  {v['sl_pct']}%  {v['rr']:5s} {v['tier_required']}")

    print()
    selections = input("  Select models (comma-separated, e.g. 1,3,4): ").strip()
    selected_indices = [int(x.strip()) - 1 for x in selections.split(",") if x.strip().isdigit()]

    selected_versions = []
    risk_config = {}
    for idx in selected_indices:
        if 0 <= idx < len(versions):
            v = versions[idx]
            selected_versions.append(v["version_code"])
            risk = input(f"  Risk per trade (%) for {v['display_name']} [1.0]: ").strip()
            risk_val = float(risk) if risk else 1.0
            risk_config[v["version_code"]] = {"risk_pct": risk_val}

    config["QUANTIVE_SUBSCRIPTIONS"] = ",".join(selected_versions)
    config["QUANTIVE_RISK_CONFIG"] = json.dumps(risk_config)

    global_risk = input("  Max open positions (global) [2]: ").strip()
    config["MAX_OPEN_POSITIONS"] = global_risk if global_risk else "2"
    config["ALLOW_SHORT"] = "true" if input_yesno("Allow SHORT signals?", "n") else "false"

    # Step 5: Save
    print_header("[5/5] SUMMARY & SAVE")
    print(f"  Exchange:  {config.get('EXCHANGE', 'N/A').upper()}")
    print(f"  Telegram:  {'Enabled' if config.get('TELEGRAM_BOT_TOKEN') else 'Disabled'}")
    print(f"  Models:    {len(selected_versions)} selected")
    for vc in selected_versions:
        print(f"    • {vc} — risk {risk_config.get(vc, {}).get('risk_pct', 1.0)}%")

    if input_yesno("Save configuration?", "y"):
        _save_config(config)
        print(f"\n  Configuration saved to {CONFIG_FILE}")
        print(f"  Run:  quantive-terminal test    (verify connection)")
        print(f"        quantive-terminal run     (start trading)")
    else:
        print("  Setup cancelled")


def _save_config(config):
    lines = [
        "# Generated by quantive-terminal setup",
        f"QUANTIVE_API_BASE={API_BASE}",
        f"QUANTIVE_API_KEY={config.get('QUANTIVE_API_KEY', '')}",
        "",
        f"EXCHANGE={config.get('EXCHANGE', 'binance')}",
        f"EXCHANGE_API_KEY={config.get('EXCHANGE_API_KEY', '')}",
        f"EXCHANGE_API_SECRET={config.get('EXCHANGE_API_SECRET', '')}",
        f"EXCHANGE_TESTNET={config.get('EXCHANGE_TESTNET', 'false')}",
        "",
        f"RISK_PCT_PER_TRADE=1.0",
        f"MAX_OPEN_POSITIONS={config.get('MAX_OPEN_POSITIONS', '2')}",
        f"MAX_SLIPPAGE_PCT=0.3",
        f"ALLOW_SHORT={config.get('ALLOW_SHORT', 'false')}",
        "",
        f"QUANTIVE_SUBSCRIPTIONS={config.get('QUANTIVE_SUBSCRIPTIONS', '')}",
        f"QUANTIVE_RISK_CONFIG={config.get('QUANTIVE_RISK_CONFIG', '{}')}",
        "",
        f"TELEGRAM_BOT_TOKEN={config.get('TELEGRAM_BOT_TOKEN', '')}",
        f"TELEGRAM_CHAT_ID={config.get('TELEGRAM_CHAT_ID', '')}",
        "",
        "POLL_INTERVAL_SEC=2",
        "LOG_LEVEL=INFO",
        "ORPHAN_ACTION=close",
    ]
    with open(CONFIG_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
