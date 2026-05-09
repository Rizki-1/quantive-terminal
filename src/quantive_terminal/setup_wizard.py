import os
import re
import requests
import json
import sys
import socket
from .fingerprint import get_fingerprint

CONFIG_FILE = ".env"
API_BASE = "https://dash.quantive.my.id"

TIER_LABEL = {"trial": "TRIAL", "free": "FREE", "pro": "PRO", "vip": "VIP", "admin": "ADMIN"}
TIER_LEVEL = {"trial": 0, "free": 1, "pro": 2, "vip": 3, "admin": 99}

LOCK_ICON = "[LOCKED]"
CHECK_ICON = "[OK]"
WARN_ICON  = "[WARN]"
FAIL_ICON  = "[FAIL]"


def print_header(text):
    print(f"\n{'='*58}")
    print(f"  {text}")
    print(f"{'='*58}")


def print_divider():
    print(f"  {'-'*54}")


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


def input_float(prompt, default=1.0, min_val=0.1, max_val=10.0):
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = float(raw)
            if min_val <= val <= max_val:
                return val
            print(f"  Value must be between {min_val} and {max_val}")
        except ValueError:
            print("  Please enter a number (e.g. 1.0 or 0.5)")


def _fetch_me(api_key):
    """Fetch user profile + subscriptions from server. Returns dict or None."""
    try:
        r = requests.get(
            f"{API_BASE}/api/v1/auth/me",
            headers={"X-Quantive-Key": api_key},
            timeout=10,
        )
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def _fetch_versions(api_key):
    """Fetch all public versions. Returns list."""
    try:
        r = requests.get(
            f"{API_BASE}/api/v1/versions",
            headers={"X-Quantive-Key": api_key},
            timeout=10,
        )
        if r.ok:
            return r.json()
    except Exception:
        pass
    return []


def _push_version_config(api_key, version_code, risk_pct, allow_short=False, max_open=1):
    """Push per-model risk config to server."""
    try:
        requests.post(
            f"{API_BASE}/api/v1/me/config/{version_code}",
            headers={"X-Quantive-Key": api_key, "Content-Type": "application/json"},
            json={
                "risk_pct_per_trade": risk_pct,
                "allow_short": allow_short,
                "max_open_positions": max_open,
            },
            timeout=10,
        )
    except Exception:
        pass


def _select_models_single(subscribed_versions, versions_map):
    """Handle single-scope license: 1 model pre-selected, just configure risk."""
    vc = subscribed_versions[0]
    v = versions_map.get(vc, {})
    display = v.get("display_name", vc)

    print(f"\n  Your license includes 1 model:")
    print(f"  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  {display:<51}│")
    tp  = v.get("tp_pct", "?")
    sl  = v.get("sl_pct", "?")
    rr  = v.get("rr",     "?")
    print(f"  │  TP: {tp}%   SL: {sl}%   RR: {rr:<36}│")
    print(f"  └─────────────────────────────────────────────────────┘")
    print()

    risk = input_float(f"Risk per trade (%) for {v.get('asset', vc)}", default=1.0)
    return [vc], {vc: {"risk_pct": risk}}


def _select_models_multi(subscribed_set, max_versions, all_versions, user_tier):
    """Handle multi-scope license: show all models with lock status, let user select subset."""
    included = [v for v in all_versions if v.get("version_code") in subscribed_set]
    locked   = [v for v in all_versions if v.get("version_code") not in subscribed_set]

    user_tier_lvl = TIER_LEVEL.get(user_tier, 0)

    print(f"\n  {'#':>2}  {'Model':<42} {'TP':>5} {'SL':>5} {'RR':>5}  Status")
    print_divider()

    row_index = {}  # display index → version_code
    i = 1
    for v in included:
        vc = v["version_code"]
        row_index[i] = vc
        print(
            f"  {i:>2}  {v['display_name']:<42} "
            f"{v.get('tp_pct', 0):>4.1f}% {v.get('sl_pct', 0):>4.1f}%  "
            f"{v.get('rr','?'):>5}  {CHECK_ICON}"
        )
        i += 1

    if locked:
        print()
        for v in locked:
            req_tier = v.get("tier_required", "pro").upper()
            print(
                f"  {'':>2}  {v['display_name']:<42} "
                f"{v.get('tp_pct', 0):>4.1f}% {v.get('sl_pct', 0):>4.1f}%  "
                f"{v.get('rr','?'):>5}  {LOCK_ICON} (needs {req_tier})"
            )

    if not included:
        print("  No accessible models found. Check your license tier.")
        return [], {}

    print()
    if max_versions < 99:
        print(f"  Your license allows up to {max_versions} model(s).")

    sel_raw = input(
        "  Select models to activate (comma-separated numbers, or 'all'): "
    ).strip().lower()

    if sel_raw == "all":
        selected_indices = list(row_index.keys())
    else:
        selected_indices = []
        for part in sel_raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part)
                if idx in row_index:
                    selected_indices.append(idx)
                else:
                    print(f"  {WARN_ICON} Index {idx} not in your license — skipped")

    if max_versions < 99 and len(selected_indices) > max_versions:
        print(
            f"  {WARN_ICON} You selected {len(selected_indices)} but license allows {max_versions}. "
            f"Using first {max_versions}."
        )
        selected_indices = selected_indices[:max_versions]

    if not selected_indices:
        print(f"  {WARN_ICON} No valid models selected.")
        return [], {}

    selected_vcs = [row_index[idx] for idx in selected_indices]

    print()
    risk_config = {}
    versions_map = {v["version_code"]: v for v in all_versions}
    for vc in selected_vcs:
        v = versions_map.get(vc, {})
        asset = v.get("asset", vc.split("_")[0])
        display = v.get("display_name", vc)
        print(f"  Model: {display}")
        risk = input_float(f"  Risk per trade (%) for {asset}", default=1.0)
        risk_config[vc] = {"risk_pct": risk}

    return selected_vcs, risk_config


def run_setup():
    config = {}
    print_header("QUANTIVE TERMINAL — SETUP WIZARD v2")

    # ── Step 1: License ───────────────────────────────────────────
    print_header("[1/5] LICENSE KEY")
    print("  [1] Activate with license key")
    print("  [2] Start FREE TRIAL (3 days, 1 model)")
    choice = input("  > ").strip()

    email       = input_required("Enter your email")
    fingerprint = get_fingerprint()

    if choice == "2":
        print("  Starting free trial...")
        try:
            r = requests.post(f"{API_BASE}/api/v1/license/activate", json={
                "trial":       True,
                "email":       email,
                "fingerprint": fingerprint,
                "hostname":    socket.gethostname(),
            }, timeout=10)
            data = r.json()
            if data.get("success"):
                config["QUANTIVE_API_KEY"] = data["api_key"]
                days = data.get("days_remaining", 3)
                tier = data.get("tier", "trial")
                print(f"  {CHECK_ICON} Trial activated!  Tier: {TIER_LABEL.get(tier, tier)}  "
                      f"({days} days remaining)")
            else:
                print(f"  {FAIL_ICON} Trial failed: {data.get('message', 'Unknown error')}")
                if input_yesno("Retry with license key?", "y"):
                    choice = "1"
                else:
                    sys.exit(1)
        except Exception as e:
            print(f"  {FAIL_ICON} Connection failed: {e}")
            sys.exit(1)

    if choice == "1":
        license_key = input_required("Enter license key")
        print("  Verifying license...")
        try:
            r = requests.post(f"{API_BASE}/api/v1/license/activate", json={
                "license_key": license_key,
                "email":       email,
                "fingerprint": fingerprint,
                "hostname":    socket.gethostname(),
            }, timeout=10)
            data = r.json()
            if data.get("success"):
                config["QUANTIVE_API_KEY"] = data["api_key"]
                tier = data.get("tier", "pro")
                print(f"  {CHECK_ICON} License activated!  Tier: {TIER_LABEL.get(tier, tier)}")
                if data.get("expires_at"):
                    print(f"  Expires: {data['expires_at'][:10]}")
            else:
                print(f"  {FAIL_ICON} Activation failed: {data.get('message', 'Unknown error')}")
                sys.exit(1)
        except Exception as e:
            print(f"  {FAIL_ICON} Connection failed: {e}")
            sys.exit(1)

    # ── Step 2: Exchange ──────────────────────────────────────────
    print_header("[2/5] EXCHANGE")
    exchange = input_choice("Select exchange:", [
        ("binance", "Binance Futures (USDT-M)"),
        ("bybit",   "Bybit Perpetuals"),
        ("lighter", "Lighter DEX"),
    ])
    config["EXCHANGE"]            = exchange
    config["EXCHANGE_API_KEY"]    = input_required("Enter API Key")
    config["EXCHANGE_API_SECRET"] = input_required("Enter API Secret")
    config["EXCHANGE_TESTNET"]    = "true" if input_yesno("Use testnet?", "n") else "false"

    # ── Step 3: Telegram ──────────────────────────────────────────
    print_header("[3/5] TELEGRAM NOTIFICATIONS (Optional)")
    bot_token = input("  Bot Token (Enter to skip): ").strip()
    if bot_token:
        chat_id = input_required("Chat ID")
        config["TELEGRAM_BOT_TOKEN"] = bot_token
        config["TELEGRAM_CHAT_ID"]   = chat_id
        print(f"  {CHECK_ICON} Telegram configured")
    else:
        print("  Skipped")

    # ── Step 4: Model + Risk ──────────────────────────────────────
    print_header("[4/5] MODEL SELECTION & RISK CONFIG")
    api_key = config["QUANTIVE_API_KEY"]

    # Fetch user profile (subscriptions granted by license)
    print("  Fetching your license profile...")
    me = _fetch_me(api_key)
    if not me:
        print(f"  {WARN_ICON} Could not fetch profile — using fallback defaults")
        me = {}

    user_tier    = me.get("tier", "pro")
    max_versions = me.get("max_versions", 1)
    server_subs  = [s["version_code"] for s in me.get("subscriptions", [])]

    # Show license summary
    scope_label = "ALL MODELS" if max_versions >= 99 else f"SINGLE MODEL"
    print(f"\n  License tier   : {TIER_LABEL.get(user_tier, user_tier.upper())}")
    print(f"  License scope  : {scope_label}")
    print(f"  Subscriptions  : {len(server_subs)} model(s) included")

    # Fetch all public versions for display
    print("  Fetching available models...")
    all_versions = _fetch_versions(api_key)
    if not all_versions:
        # Hard-coded fallback
        all_versions = [
            {"version_code": "BTC_1H_V1_RR2", "display_name": "BTC V1 — RR 1:2 (base features)",       "asset": "BTC", "tp_pct": 3.0, "sl_pct": 1.5, "rr": "1:2", "tier_required": "pro"},
            {"version_code": "ETH_1H_V1_RR2", "display_name": "ETH V1 — RR 1:2 (HTF + time features)", "asset": "ETH", "tp_pct": 3.0, "sl_pct": 1.5, "rr": "1:2", "tier_required": "pro"},
            {"version_code": "BTC_1H_V3_RR2", "display_name": "BTC V3 — Dow strict LONG RR 1:2",       "asset": "BTC", "tp_pct": 3.0, "sl_pct": 1.5, "rr": "1:2", "tier_required": "vip"},
            {"version_code": "BNB_1H_V1_RR2", "display_name": "BNB V1 — RR 1:2",                       "asset": "BNB", "tp_pct": 3.0, "sl_pct": 1.5, "rr": "1:2", "tier_required": "pro"},
            {"version_code": "SOL_1H_V1_RR2", "display_name": "SOL V1 — RR 1:2 (WR 61%)",              "asset": "SOL", "tp_pct": 3.0, "sl_pct": 1.5, "rr": "1:2", "tier_required": "pro"},
        ]

    # Determine subscribed set: prefer server response, fall back to tier-based
    if server_subs:
        subscribed_set = set(server_subs)
    else:
        # No server data: grant access based on tier
        user_tier_lvl = TIER_LEVEL.get(user_tier, 0)
        subscribed_set = {
            v["version_code"] for v in all_versions
            if TIER_LEVEL.get(v.get("tier_required", "pro"), 0) <= user_tier_lvl
        }

    versions_map = {v["version_code"]: v for v in all_versions}

    print()
    if max_versions == 1 or len(subscribed_set) == 1:
        # Single-scope license
        if not subscribed_set:
            print(f"  {FAIL_ICON} No models in your license. Contact support.")
            sys.exit(1)
        vc_list = list(subscribed_set)[:1]
        selected_versions, risk_config = _select_models_single(vc_list, versions_map)
    else:
        # Multi/all-scope license
        selected_versions, risk_config = _select_models_multi(
            subscribed_set, max_versions, all_versions, user_tier
        )

    if not selected_versions:
        print(f"  {FAIL_ICON} No models activated. Exiting.")
        sys.exit(1)

    config["QUANTIVE_SUBSCRIPTIONS"] = ",".join(selected_versions)
    config["QUANTIVE_RISK_CONFIG"]    = json.dumps(risk_config)

    # Global settings
    print()
    print_divider()
    max_pos_default = str(len(selected_versions))
    max_pos = input(f"  Max concurrent open positions [{max_pos_default}]: ").strip()
    config["MAX_OPEN_POSITIONS"] = max_pos if max_pos.isdigit() else max_pos_default
    config["ALLOW_SHORT"] = "true" if input_yesno("Allow SHORT signals?", "n") else "false"

    # Push per-model risk configs to server (best-effort)
    allow_short_flag = config["ALLOW_SHORT"] == "true"
    max_pos_int      = int(config["MAX_OPEN_POSITIONS"])
    print()
    for vc, rc in risk_config.items():
        _push_version_config(
            api_key, vc, rc["risk_pct"],
            allow_short=allow_short_flag,
            max_open=max_pos_int,
        )
    print(f"  {CHECK_ICON} Risk config synced to server")

    # ── Step 5: Summary & Save ────────────────────────────────────
    print_header("[5/5] SUMMARY & SAVE")
    print(f"  License tier : {TIER_LABEL.get(user_tier, user_tier.upper())}")
    print(f"  Exchange     : {config.get('EXCHANGE', '').upper()}")
    print(f"  Telegram     : {'Enabled' if config.get('TELEGRAM_BOT_TOKEN') else 'Disabled'}")
    print(f"  Models ({len(selected_versions)} active):")
    for vc in selected_versions:
        v    = versions_map.get(vc, {})
        risk = risk_config.get(vc, {}).get("risk_pct", 1.0)
        print(f"    • {v.get('display_name', vc):<44}  risk: {risk}%")
    print(f"  Max positions: {config['MAX_OPEN_POSITIONS']}")
    print(f"  Allow SHORT  : {config['ALLOW_SHORT']}")

    if input_yesno("\n  Save configuration?", "y"):
        _save_config(config)
        print(f"\n  {CHECK_ICON} Configuration saved to {CONFIG_FILE}")
        print(f"\n  Next steps:")
        print(f"    quantive-terminal test    — verify all connections")
        print(f"    quantive-terminal run     — start live signal executor")
    else:
        print("  Setup cancelled.")


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
