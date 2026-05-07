import argparse
import logging
import sys

from . import config
from .exchanges.binance import BinanceExchange
from .exchanges.bybit import BybitExchange
from .executor import Executor
from .connect_test import run_connect_test
from .setup_wizard import run_setup


def main():
    parser = argparse.ArgumentParser(
        prog="quantive-terminal",
        description="Self-hosted signal executor for automated crypto trading",
    )
    sub = parser.add_subparsers(dest="command", help="Commands")

    sub.add_parser("setup", help="Interactive setup wizard")
    sub.add_parser("test", help="Test connection to Quantive API and exchange")
    sub.add_parser("run", help="Start signal listener and trade executor")
    sub.add_parser("status", help="Show current positions and state")

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.command == "setup":
        run_setup()

    elif args.command == "test":
        ok = run_connect_test()
        sys.exit(0 if ok else 1)

    elif args.command == "run":
        errors = config.validate()
        if errors:
            print("Configuration errors:")
            for e in errors:
                print(f"  - {e}")
            print("\nRun 'quantive-terminal setup' first.")
            sys.exit(1)

        name = config.EXCHANGE.lower()
        if name == "binance":
            exchange = BinanceExchange(
                config.EXCHANGE_API_KEY, config.EXCHANGE_API_SECRET, config.EXCHANGE_TESTNET
            )
        elif name == "bybit":
            exchange = BybitExchange(
                config.EXCHANGE_API_KEY, config.EXCHANGE_API_SECRET, config.EXCHANGE_TESTNET
            )
        else:
            print(f"Unsupported exchange: {name}")
            sys.exit(1)

        executor = Executor(exchange)
        executor.reconcile_on_startup(config.ORPHAN_ACTION)
        executor.run_loop(config.POLL_INTERVAL_SEC)

    elif args.command == "status":
        from position_manager import PositionManager
        pm = PositionManager()
        positions = pm.get_open_positions()
        if positions:
            print(f"Open positions ({len(positions)}):")
            for p in positions:
                print(f"  {p['version_code']} {p['side']} entry={p['entry_price']} size={p['size']}")
        else:
            print("No open positions")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
