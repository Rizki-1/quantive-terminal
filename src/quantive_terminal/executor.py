import logging
import time
from datetime import datetime, timezone
from .signal_client import SignalClient
from .deduplicator import Deduplicator
from .risk_manager import RiskManager
from .position_manager import PositionManager
from .notifier import Notifier

log = logging.getLogger(__name__)


class Executor:
    def __init__(self, exchange):
        self.exchange = exchange
        self.signal_client = SignalClient()
        self.dedup = Deduplicator()
        self.risk = RiskManager(exchange)
        self.positions = PositionManager()
        self.notifier = Notifier()

    def process_signal(self, signal):
        signal_id = signal.get("signal_id", "")
        action = signal.get("action", "OPEN").upper()
        version = signal.get("version_code", "")

        if self.dedup.is_duplicate(signal_id):
            return

        if action == "OPEN":
            self._handle_open(signal)
        elif action == "CLOSE":
            self._handle_close(signal)
        elif action == "MODIFY_SL":
            self._handle_modify_sl(signal)
        elif action == "MODIFY_TP":
            self._handle_modify_tp(signal)

        self.dedup.mark_processed(signal_id)

    def _handle_open(self, signal):
        signal_id = signal["signal_id"]
        side = signal.get("side", "LONG").upper()
        symbol = signal.get("symbol_hint", signal.get("asset", "BTC") + "USDT")
        version = signal.get("version_code", "")

        ok, result = self.risk.evaluate(signal, self.positions.get_open_count())
        if not ok:
            log.info(f"Signal rejected: {result}")
            return

        equity = result["equity"]
        size = result["size"]

        order = self.exchange.market_order(symbol, side.lower(), size)
        if not order:
            log.error("Order failed")
            return

        entry_price = float(order.get("price", order.get("average", 0)))
        tp_val = None
        sl_val = None
        tp_list = signal.get("tp", [])
        if tp_list:
            tp_val = float(tp_list[0].get("value", 0))
        sl = signal.get("sl", {})
        if sl:
            sl_val = float(sl.get("value", 0))

        self.positions.open_position(signal_id, version, side, entry_price, size, tp_val, sl_val)
        self.notifier.send_trade_open(signal, entry_price, size)

    def _handle_close(self, signal):
        signal_id = signal.get("signal_id", "")
        position_id = signal.get("position_id", signal_id)
        symbol = signal.get("symbol_hint", signal.get("asset", "BTC") + "USDT")

        current = self.exchange.fetch_ticker(symbol)
        if current <= 0:
            log.error("Cannot fetch price for close")
            return

        result = self.exchange.close_position(symbol)
        if result:
            self.positions.close_position(position_id, current, reason="signal_close")
            self.notifier.send_trade_close(signal, current)
        else:
            self.positions.close_position(position_id, current, reason="signal_close_no_order")

    def _handle_modify_sl(self, signal):
        log.info(f"MODIFY_SL: {signal.get('signal_id')}")

    def _handle_modify_tp(self, signal):
        log.info(f"MODIFY_TP: {signal.get('signal_id')}")

    def run_loop(self, poll_interval=2):
        log.info("Starting signal loop...")
        self.dedup.cleanup()

        while True:
            try:
                signals = self.signal_client.poll_signals()
                if signals:
                    for s in signals:
                        self.process_signal(s)
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                log.info("Shutting down...")
                break
            except Exception as e:
                log.error(f"Loop error: {e}")
                time.sleep(poll_interval)

    def reconcile_on_startup(self, orphan_action="close"):
        exchange_positions = self.exchange.fetch_open_positions()
        orphans = self.positions.reconcile(exchange_positions, orphan_action)

        for sid, pos in orphans:
            log.warning(f"Orphan position: {sid} {pos['side']} entry={pos['entry_price']}")
            if orphan_action == "close":
                # version_code looks like BTC_1H_V1_RR2 — first part is asset
                vc = pos.get("version_code", "")
                asset = vc.split("_")[0] if vc else "BTC"
                symbol = pos.get("symbol") or f"{asset}USDT"
                self.exchange.close_position(symbol)
                self.positions.close_position(sid, 0, reason="orphan_close")
