from typing import Optional


VALID_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "ADAUSDT", "XRPUSDT", "DOGEUSDT", "LINKUSDT",
    "LTCUSDT", "AVAXUSDT",
}

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP"}


class ValidationError(Exception):
    pass


def validate_symbol(symbol: str) -> str:
    s = symbol.upper().strip()
    if s not in VALID_SYMBOLS:
        raise ValidationError(
            f"Invalid symbol '{s}'. Valid: {', '.join(sorted(VALID_SYMBOLS))}"
        )
    return s


def validate_side(side: str) -> str:
    s = side.upper().strip()
    if s not in VALID_SIDES:
        raise ValidationError(f"Side must be BUY or SELL, got '{side}'")
    return s


def validate_order_type(order_type: str) -> str:
    t = order_type.upper().strip()
    if t not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type must be one of {VALID_ORDER_TYPES}, got '{order_type}'"
        )
    return t


def validate_quantity(quantity: float) -> float:
    if quantity <= 0:
        raise ValidationError(f"Quantity must be > 0, got {quantity}")
    return round(quantity, 3)


def validate_price(price: Optional[float], order_type: str) -> Optional[float]:
    if order_type in ("LIMIT", "STOP") and (price is None or price <= 0):
        raise ValidationError(f"Price is required and must be > 0 for {order_type} orders")
    if price is not None and price <= 0:
        raise ValidationError(f"Price must be > 0, got {price}")
    return round(price, 2) if price is not None else None
