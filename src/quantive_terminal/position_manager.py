import json
import os
import logging
from .config import STATE_DIR

log = logging.getLogger(__name__)

POSITIONS_FILE = os.path.join(STATE_DIR, "open_positions.json")
TRADES_FILE = os.path.join(STATE_DIR, "closed_trades.csv")


class PositionManager:
    def __init__(self):
        self.positions = self._load()
        self._ensure_trades_file()

    def _load(self):
        if os.path.exists(POSITIONS_FILE):
            try:
                with open(POSITIONS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        tmp = POSITIONS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.positions, f, indent=2)
        os.replace(tmp, POSITIONS_FILE)

    def _ensure_trades_file(self):
        if not os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, "w") as f:
                f.write("timestamp,signal_id,version_code,side,entry_price,exit_price,size,pnl,pnl_pct\n")

    def open_position(self, signal_id, version_code, side, entry_price, size, tp, sl):
        pos = {
            "signal_id": signal_id,
            "version_code": version_code,
            "side": side,
            "entry_price": entry_price,
            "size": size,
            "tp": tp,
            "sl": sl,
            "opened_at": signal_id.split("-")[1] if "-" in signal_id else "",
        }
        self.positions[signal_id] = pos
        self._save()
        log.info(f"Position opened: {side} size={size:.4f} entry={entry_price}")

    def close_position(self, signal_id, exit_price, reason="manual"):
        pos = self.positions.pop(signal_id, None)
        if not pos:
            return None

        entry = float(pos["entry_price"])
        size = float(pos["size"])
        side = pos["side"]

        if side.upper() == "SHORT":
            pnl = (entry - exit_price) * size
        else:
            pnl = (exit_price - entry) * size

        pnl_pct = (exit_price / entry - 1) * 100 if side.upper() == "LONG" else (entry / exit_price - 1) * 100

        self._save()
        self._log_trade(pos, exit_price, pnl, pnl_pct, reason)
        log.info(f"Position closed: {side} pnl={pnl:.2f} ({pnl_pct:.2f}%) reason={reason}")

        return {"entry": entry, "exit": exit_price, "pnl": pnl, "pnl_pct": pnl_pct}

    def _log_trade(self, pos, exit_price, pnl, pnl_pct, reason):
        import datetime
        ts = datetime.datetime.now().isoformat()
        line = f"{ts},{pos['signal_id']},{pos['version_code']},{pos['side']},{pos['entry_price']},{exit_price},{pos['size']},{pnl:.4f},{pnl_pct:.2f}\n"
        with open(TRADES_FILE, "a") as f:
            f.write(line)

    def get_open_positions(self):
        return list(self.positions.values())

    def get_open_count(self):
        return len(self.positions)

    def reconcile(self, exchange_positions, orphan_action="close"):
        local_ids = set(self.positions.keys())
        exchange_symbols = {p.get("symbol", "") for p in exchange_positions}

        orphan = []
        for sid, pos in self.positions.items():
            found = any(
                pos.get("version_code", "").split("_")[0] in p.get("symbol", "")
                for p in exchange_positions
            )
            if not found:
                orphan.append((sid, pos))

        return orphan
