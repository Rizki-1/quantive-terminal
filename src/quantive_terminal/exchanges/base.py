import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class BaseExchange(ABC):
    @abstractmethod
    def fetch_balance(self):
        pass

    @abstractmethod
    def fetch_ticker(self, symbol):
        pass

    @abstractmethod
    def market_order(self, symbol, side, amount, params=None):
        pass

    @abstractmethod
    def fetch_open_positions(self, symbol=None):
        pass

    @abstractmethod
    def close_position(self, symbol, amount=None):
        pass
