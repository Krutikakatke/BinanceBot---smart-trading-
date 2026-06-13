from typing import Any, Dict, Optional

from .client import BinanceClient
from .logging_config import get_logger
from .validators import (
    validate_order_type, validate_price,
    validate_quantity, validate_side, validate_symbol,
)

logger = get_logger("orders")


class OrderManager:
    def __init__(self, client: BinanceClient):
        self.client = client

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        # Validate
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        order_type = validate_order_type(order_type)
        quantity = validate_quantity(quantity)
        price = validate_price(price, order_type)

        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force

        if order_type in ("STOP", "STOP_MARKET") and stop_price:
            params["stopPrice"] = round(stop_price, 2)
            if order_type == "STOP":
                params["price"] = price
                params["timeInForce"] = time_in_force

        logger.info(
            "Placing %s %s %s | qty=%s price=%s",
            order_type, side, symbol, quantity, price
        )

        response = self.client._post("/fapi/v1/order", params)
        logger.info("Order placed — orderId=%s status=%s", response.get("orderId"), response.get("status"))
        return response

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self.client._get("/fapi/v1/openOrders", params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        params = {"symbol": symbol.upper(), "orderId": order_id}
        logger.info("Cancelling order %s on %s", order_id, symbol)
        return self.client._post("/fapi/v1/order", params)


def format_order_result(order: Dict[str, Any]) -> str:
    lines = [
        "",
        "╔══════════════════════════════════════╗",
        "║         ORDER RESULT SUMMARY         ║",
        "╠══════════════════════════════════════╣",
        f"║  Order ID    : {str(order.get('orderId', '--')).ljust(22)}║",
        f"║  Symbol      : {str(order.get('symbol', '--')).ljust(22)}║",
        f"║  Side        : {str(order.get('side', '--')).ljust(22)}║",
        f"║  Type        : {str(order.get('type', '--')).ljust(22)}║",
        f"║  Status      : {str(order.get('status', '--')).ljust(22)}║",
        f"║  Quantity    : {str(order.get('origQty', '--')).ljust(22)}║",
        f"║  Exec Qty    : {str(order.get('executedQty', '--')).ljust(22)}║",
        f"║  Avg Price   : {str(order.get('avgPrice', '--')).ljust(22)}║",
        f"║  Price       : {str(order.get('price', '--')).ljust(22)}║",
        "╚══════════════════════════════════════╝",
    ]
    return "\n".join(lines)
