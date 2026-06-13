#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI Entry Point
"""
import argparse
import os
import sys

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import get_logger
from bot.orders import OrderManager, format_order_result
from bot.validators import ValidationError

logger = get_logger("cli")

BANNER = """
\033[92m
  ██████╗ ██╗███╗   ██╗ █████╗ ███╗   ██╗ ██████╗███████╗
  ██╔══██╗██║████╗  ██║██╔══██╗████╗  ██║██╔════╝██╔════╝
  ██████╔╝██║██╔██╗ ██║███████║██╔██╗ ██║██║     █████╗  
  ██╔══██╗██║██║╚██╗██║██╔══██║██║╚██╗██║██║     ██╔══╝  
  ██████╔╝██║██║ ╚████║██║  ██║██║ ╚████║╚██████╗███████╗
  ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝
\033[33m         FUTURES TESTNET BOT  ·  USDT-M PERPETUALS\033[0m
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place orders on Binance Futures Testnet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── order ──────────────────────────────────────────────────
    order_p = sub.add_parser("order", help="Place a new order")
    order_p.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    order_p.add_argument("--side", required=True, choices=["BUY", "SELL"], help="BUY or SELL")
    order_p.add_argument("--type", dest="order_type", required=True,
                         choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP"],
                         help="Order type")
    order_p.add_argument("--qty", required=True, type=float, help="Quantity (e.g. 0.01)")
    order_p.add_argument("--price", type=float, default=None,
                         help="Limit/stop price (required for LIMIT/STOP)")
    order_p.add_argument("--stop-price", type=float, default=None,
                         help="Stop trigger price (for STOP / STOP_MARKET)")
    order_p.add_argument("--tif", default="GTC",
                         choices=["GTC", "IOC", "FOK"], help="Time-in-force (default: GTC)")

    # ── price ──────────────────────────────────────────────────
    price_p = sub.add_parser("price", help="Get current mark price")
    price_p.add_argument("--symbol", required=True)

    # ── account ────────────────────────────────────────────────
    sub.add_parser("account", help="Show account balance summary")

    # ── open-orders ────────────────────────────────────────────
    oo_p = sub.add_parser("open-orders", help="List open orders")
    oo_p.add_argument("--symbol", default=None)

    return parser


def main():
    print(BANNER)
    parser = build_parser()
    args = parser.parse_args()

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print("\033[91m✖  BINANCE_API_KEY and BINANCE_API_SECRET env vars not set.\033[0m")
        print("   Export them before running:\n")
        print("   export BINANCE_API_KEY='your_key'")
        print("   export BINANCE_API_SECRET='your_secret'\n")
        sys.exit(1)

    client = BinanceClient(api_key, api_secret)

    if not client.ping():
        print("\033[91m✖  Cannot reach Binance Futures Testnet. Check your connection.\033[0m")
        sys.exit(1)

    print("\033[92m✔  Connected to Binance Futures Testnet\033[0m\n")

    try:
        if args.command == "order":
            manager = OrderManager(client)
            print(f"  → Submitting {args.order_type} {args.side} {args.symbol} | qty={args.qty} price={args.price}")
            result = manager.place_order(
                symbol=args.symbol,
                side=args.side,
                order_type=args.order_type,
                quantity=args.qty,
                price=args.price,
                stop_price=args.stop_price,
                time_in_force=args.tif,
            )
            print(format_order_result(result))
            print("\033[92m✔  Order placed successfully.\033[0m\n")

        elif args.command == "price":
            price = client.get_price(args.symbol.upper())
            print(f"  {args.symbol.upper()} current price: \033[93m{price:,.2f} USDT\033[0m\n")

        elif args.command == "account":
            acc = client.get_account()
            assets = [a for a in acc.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
            print("  ACCOUNT BALANCES")
            print("  " + "─" * 38)
            for a in assets:
                print(f"  {a['asset'].ljust(10)} Wallet: {float(a['walletBalance']):>12.4f}  "
                      f"UnPnL: {float(a.get('unrealizedProfit',0)):>+10.4f}")
            print()

        elif args.command == "open-orders":
            manager = OrderManager(client)
            orders = manager.get_open_orders(args.symbol)
            if not orders:
                print("  No open orders.\n")
            else:
                print(f"  {len(orders)} open order(s):\n")
                for o in orders:
                    print(f"  [{o['orderId']}] {o['side']} {o['type']} {o['symbol']} "
                          f"qty={o['origQty']} price={o['price']}")
                print()

    except ValidationError as e:
        logger.error("Validation error: %s", e)
        print(f"\033[91m✖  Validation error: {e}\033[0m\n")
        sys.exit(1)
    except BinanceAPIError as e:
        logger.error("API error %s: %s", e.code, e.msg)
        print(f"\033[91m✖  API error [{e.code}]: {e.msg}\033[0m\n")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        print(f"\033[91m✖  Unexpected error: {e}\033[0m\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
