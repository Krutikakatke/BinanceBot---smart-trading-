#!/usr/bin/env python3
"""
FastAPI backend — bridges the browser UI to Binance Futures Testnet
"""
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from bot.client import BinanceClient, BinanceAPIError
from bot.intelligence import backtest_signal, build_signal
from bot.orders import OrderManager
from bot.validators import ValidationError
from bot.logging_config import get_logger

logger = get_logger("server")
app = FastAPI(title="Binance Futures Testnet Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_client():
    key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_API_SECRET", "")
    if not key or not secret:
        raise HTTPException(status_code=500, detail="API keys not set. Export BINANCE_API_KEY and BINANCE_API_SECRET.")
    return BinanceClient(key, secret)


class OrderRequest(BaseModel):
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"


@app.get("/api/ping")
def ping():
    client = get_client()
    ok = client.ping()
    return {"connected": ok}


@app.get("/api/price/{symbol}")
def get_price(symbol: str):
    client = get_client()
    try:
        price = client.get_price(symbol.upper())
        return {"symbol": symbol.upper(), "price": price}
    except BinanceAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/account")
def get_account():
    client = get_client()
    try:
        acc = client.get_account()
        assets = [
            {
                "asset": a["asset"],
                "walletBalance": float(a["walletBalance"]),
                "unrealizedProfit": float(a.get("unrealizedProfit", 0)),
            }
            for a in acc.get("assets", [])
            if float(a.get("walletBalance", 0)) > 0
        ]
        total = sum(a["walletBalance"] for a in assets)
        pnl = sum(a["unrealizedProfit"] for a in assets)
        return {"totalBalance": round(total, 2), "unrealizedPnl": round(pnl, 4), "assets": assets}
    except BinanceAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_total_balance(client: BinanceClient) -> float:
    try:
        acc = client.get_account()
        return sum(
            float(a["walletBalance"])
            for a in acc.get("assets", [])
            if float(a.get("walletBalance", 0)) > 0
        )
    except Exception:
        return 0.0


@app.get("/api/ai/signal/{symbol}")
def ai_signal(symbol: str, interval: str = "15m", limit: int = 160):
    client = get_client()
    try:
        klines = client.get_klines(symbol.upper(), interval=interval, limit=limit)
        signal = build_signal(klines, balance=get_total_balance(client))
        return {"symbol": symbol.upper(), "interval": interval, **signal}
    except BinanceAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ai/backtest/{symbol}")
def ai_backtest(symbol: str, interval: str = "15m", limit: int = 300):
    client = get_client()
    try:
        klines = client.get_klines(symbol.upper(), interval=interval, limit=limit)
        result = backtest_signal(klines)
        return {"symbol": symbol.upper(), "interval": interval, **result}
    except BinanceAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/order")
def place_order(req: OrderRequest):
    client = get_client()
    manager = OrderManager(client)
    try:
        result = manager.place_order(
            symbol=req.symbol,
            side=req.side,
            order_type=req.order_type,
            quantity=req.quantity,
            price=req.price,
            stop_price=req.stop_price,
            time_in_force=req.time_in_force,
        )
        return result
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except BinanceAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/open-orders")
def open_orders(symbol: Optional[str] = None):
    client = get_client()
    manager = OrderManager(client)
    try:
        orders = manager.get_open_orders(symbol)
        return {"orders": orders}
    except BinanceAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Serve the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")
