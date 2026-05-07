import ccxt
import logging
from .base import BaseExchange

log = logging.getLogger(__name__)


class BybitExchange(BaseExchange):
    def __init__(self, api_key, api_secret, testnet=False):
        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }
        if testnet:
            config["urls"] = ccxt.bybit().describe()["urls"]
            config["urls"]["api"] = "https://api-testnet.bybit.com"
        self.exchange = ccxt.bybit(config)

    def fetch_balance(self):
        try:
            bal = self.exchange.fetch_balance({"type": "swap"})
            usdt = bal.get("USDT", {})
            return float(usdt.get("free", 0))
        except Exception as e:
            log.error(f"fetch_balance failed: {e}")
            return 0.0

    def fetch_ticker(self, symbol):
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception as e:
            log.error(f"fetch_ticker failed: {e}")
            return 0.0

    def market_order(self, symbol, side, amount, params=None):
        try:
            order = self.exchange.create_order(
                symbol, "market", side.lower(), amount, None, params or {}
            )
            log.info(f"Order executed: {side} {amount} {symbol} @ {order.get('price', 'market')}")
            return order
        except Exception as e:
            log.error(f"market_order failed: {e}")
            return None

    def fetch_open_positions(self, symbol=None):
        try:
            positions = self.exchange.fetch_positions(symbols=[symbol] if symbol else None)
            open_pos = []
            for p in positions:
                if float(p.get("contracts", 0)) != 0:
                    open_pos.append(p)
            return open_pos
        except Exception as e:
            log.error(f"fetch_open_positions failed: {e}")
            return []

    def close_position(self, symbol, amount=None):
        try:
            positions = self.fetch_open_positions(symbol)
            for p in positions:
                side = "sell" if p["side"] == "long" else "buy"
                qty = abs(float(p["contracts"]))
                return self.market_order(symbol, side, qty, {"reduceOnly": True})
        except Exception as e:
            log.error(f"close_position failed: {e}")
            return None
