from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional


@dataclass
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def parse_klines(raw_klines: List[list]) -> List[Candle]:
    return [
        Candle(
            open_time=int(k[0]),
            open=float(k[1]),
            high=float(k[2]),
            low=float(k[3]),
            close=float(k[4]),
            volume=float(k[5]),
        )
        for k in raw_klines
    ]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return mean(values[-period:])


def ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    current = mean(values[:period])
    for value in values[period:]:
        current = (value - current) * multiplier + current
    return current


def rsi(values: List[float], period: int = 14) -> Optional[float]:
    if len(values) <= period:
        return None
    gains: List[float] = []
    losses: List[float] = []
    for i in range(-period, 0):
        delta = values[i] - values[i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
    avg_gain = mean(gains)
    avg_loss = mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(candles: List[Candle], period: int = 14) -> Optional[float]:
    if len(candles) <= period:
        return None
    ranges = []
    for i in range(-period, 0):
        current = candles[i]
        prev_close = candles[i - 1].close
        ranges.append(
            max(
                current.high - current.low,
                abs(current.high - prev_close),
                abs(current.low - prev_close),
            )
        )
    return mean(ranges)


def slope_score(values: List[float], period: int = 24) -> float:
    if len(values) < period:
        return 0.0
    window = values[-period:]
    x_mean = (period - 1) / 2
    y_mean = mean(window)
    numerator = sum((i - x_mean) * (value - y_mean) for i, value in enumerate(window))
    denominator = sum((i - x_mean) ** 2 for i in range(period)) or 1
    slope = numerator / denominator
    return clamp((slope / window[-1]) * period * 35, -1, 1)


def build_signal(raw_klines: List[list], balance: Optional[float] = None) -> Dict[str, Any]:
    candles = parse_klines(raw_klines)
    if len(candles) < 50:
        return {
            "action": "HOLD",
            "confidence": 0,
            "reason": "Need at least 50 candles for a useful signal.",
            "metrics": {},
            "risk": {},
        }

    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    last = closes[-1]
    ema_fast = ema(closes, 12) or last
    ema_slow = ema(closes, 26) or last
    rsi_14 = rsi(closes, 14) or 50
    atr_14 = atr(candles, 14) or 0

    returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
    recent_vol = pstdev(returns[-24:]) if len(returns) >= 24 else 0
    trend = clamp(((ema_fast - ema_slow) / last) * 80, -1, 1)
    momentum = slope_score(closes, 24)
    rsi_component = clamp((50 - abs(rsi_14 - 50)) / 50, 0, 1)
    volume_push = 0.0
    avg_volume = sma(volumes, 30) or volumes[-1]
    if avg_volume:
        volume_push = clamp((volumes[-1] / avg_volume - 1) / 2, -0.4, 0.4)

    score = (0.38 * trend) + (0.34 * momentum) + (0.18 * trend * rsi_component) + (0.10 * volume_push)
    if score > 0.18:
        action = "BUY"
    elif score < -0.18:
        action = "SELL"
    else:
        action = "HOLD"

    confidence = int(clamp(45 + abs(score) * 55 - recent_vol * 900, 0, 95))
    atr_pct = (atr_14 / last) if last else 0
    stop_distance = max(atr_14 * 1.6, last * 0.003)
    take_distance = stop_distance * 2
    stop_loss = last - stop_distance if action == "BUY" else last + stop_distance
    take_profit = last + take_distance if action == "BUY" else last - take_distance
    risk_usdt = (balance or 0) * 0.01
    quantity = risk_usdt / stop_distance if stop_distance else 0

    if action == "HOLD":
        reason = "Market edge is weak; signal score is near neutral."
        quantity = 0
    elif action == "BUY":
        reason = "Fast trend and recent momentum lean bullish."
    else:
        reason = "Fast trend and recent momentum lean bearish."

    return {
        "action": action,
        "score": round(score, 3),
        "confidence": confidence,
        "reason": reason,
        "metrics": {
            "price": round(last, 4),
            "emaFast": round(ema_fast, 4),
            "emaSlow": round(ema_slow, 4),
            "rsi": round(rsi_14, 2),
            "atr": round(atr_14, 4),
            "atrPct": round(atr_pct * 100, 3),
            "volatilityPct": round(recent_vol * 100, 3),
        },
        "risk": {
            "riskPct": 1.0,
            "suggestedQty": round(max(quantity, 0), 3),
            "stopLoss": round(stop_loss, 2),
            "takeProfit": round(take_profit, 2),
            "riskUsdt": round(risk_usdt, 2),
        },
    }


def backtest_signal(raw_klines: List[list], starting_balance: float = 10000.0) -> Dict[str, Any]:
    candles = parse_klines(raw_klines)
    if len(candles) < 80:
        return {"trades": 0, "winRate": 0, "pnl": 0, "endingBalance": starting_balance}

    balance = starting_balance
    trades = []
    for i in range(60, len(candles) - 4):
        sample = candles[: i + 1]
        signal = build_signal([
            [c.open_time, c.open, c.high, c.low, c.close, c.volume] for c in sample
        ], balance)
        if signal["action"] == "HOLD" or signal["confidence"] < 55:
            continue
        entry = candles[i].close
        exit_price = candles[i + 4].close
        direction = 1 if signal["action"] == "BUY" else -1
        risk_usdt = balance * 0.01
        stop_distance = abs(entry - signal["risk"]["stopLoss"]) or entry * 0.003
        qty = risk_usdt / stop_distance
        pnl = (exit_price - entry) * qty * direction
        balance += pnl
        trades.append(pnl)

    wins = [p for p in trades if p > 0]
    return {
        "trades": len(trades),
        "winRate": round((len(wins) / len(trades) * 100) if trades else 0, 1),
        "pnl": round(balance - starting_balance, 2),
        "endingBalance": round(balance, 2),
        "avgTrade": round(mean(trades), 2) if trades else 0,
    }
