import logging
from datetime import datetime, timezone
from .config import MAX_SLIPPAGE_PCT, ALLOW_SHORT, MAX_OPEN_POSITIONS, get_risk_for

log = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, exchange):
        self.exchange = exchange

    def check_balance(self):
        equity = self.exchange.fetch_balance()
        if equity <= 0:
            log.warning("Balance is zero or could not be fetched")
        return equity

    def check_slippage(self, signal):
        symbol = self._symbol(signal)
        current = self.exchange.fetch_ticker(symbol)
        if current <= 0:
            return False, "Cannot fetch current price"

        ref = float(signal.get("entry", {}).get("ref_price", 0))
        if ref <= 0:
            return True, None

        slippage = abs(current - ref) / ref * 100
        max_slip = float(signal.get("entry", {}).get("max_slippage_pct", MAX_SLIPPAGE_PCT))

        if slippage > max_slip:
            return False, f"Slippage {slippage:.2f}% > {max_slip}% (ref={ref}, now={current})"

        return True, None

    def check_valid_until(self, signal):
        valid = signal.get("valid_until", "")
        if not valid:
            return True
        try:
            valid_dt = datetime.fromisoformat(valid.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > valid_dt:
                return False
        except Exception:
            pass
        return True

    def check_side_allowed(self, signal):
        side = signal.get("side", "").upper()
        if side == "SHORT" and not ALLOW_SHORT:
            return False
        return True

    def check_max_positions(self, current_open_count):
        if current_open_count >= MAX_OPEN_POSITIONS:
            return False
        return True

    def calculate_position_size(self, signal, equity):
        risk_pct = get_risk_for(signal.get("version_code", ""))
        sl_pct = float(signal.get("risk_hint", {}).get("sl_pct", 3.0)) / 100

        risk_amount = equity * (risk_pct / 100)
        if sl_pct > 0:
            position_size = risk_amount / sl_pct
        else:
            position_size = equity * 0.01

        return position_size

    def _symbol(self, signal):
        symbol = signal.get("symbol_hint", "")
        if not symbol:
            asset = signal.get("asset", "BTC")
            symbol = f"{asset}USDT"
        return symbol

    def evaluate(self, signal, current_open_count):
        if not self.check_valid_until(signal):
            return False, "Signal expired"

        if not self.check_side_allowed(signal):
            return False, "SHORT disabled"

        if not self.check_max_positions(current_open_count):
            return False, "Max positions reached"

        equity = self.check_balance()
        if equity <= 0:
            return False, "No balance"

        ok, reason = self.check_slippage(signal)
        if not ok:
            return False, reason

        size = self.calculate_position_size(signal, equity)
        return True, {"equity": equity, "size": size}
