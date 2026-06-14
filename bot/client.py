import hashlib
import hmac
import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode
import numpy

import requests

from .logging_config import get_logger

logger = get_logger("client")

BASE_URL = "https://demo-fapi.binance.com"


class BinanceClient:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        logger.info("BinanceClient initialised — endpoint: %s", BASE_URL)

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = sig
        return params

    def _get(self, path: str, params: Dict[str, Any] = None, signed: bool = False):
        params = params or {}
        if signed:
            params = self._sign(params)
        url = BASE_URL + path
        logger.debug("GET %s | params=%s", url, params)
        try:
            resp = self.session.get(url, params=params, timeout=10)
            return self._handle(resp)
        except requests.exceptions.ConnectionError as e:
            logger.error("Network error on GET %s: %s", path, e)
            raise

    def _post(self, path: str, params: Dict[str, Any] = None, signed: bool = True):
        params = params or {}
        if signed:
            params = self._sign(params)
        url = BASE_URL + path
        logger.debug("POST %s | params=%s", url, {k: v for k, v in params.items() if k != "signature"})
        try:
            resp = self.session.post(url, data=params, timeout=10)
            return self._handle(resp)
        except requests.exceptions.ConnectionError as e:
            logger.error("Network error on POST %s: %s", path, e)
            raise

    def _handle(self, resp: requests.Response) -> Dict[str, Any]:
        logger.debug("Response %s: %s", resp.status_code, resp.text[:500])
        try:
            data = resp.json()
        except ValueError:
            logger.error("Non-JSON response: %s", resp.text)
            resp.raise_for_status()
            return {}

        if resp.status_code != 200 or "code" in data and data["code"] != 200:
            code = data.get("code", resp.status_code)
            msg = data.get("msg", "Unknown API error")
            logger.error("API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg)

        return data

    def ping(self) -> bool:
        try:
            self._get("/fapi/v1/ping")
            return True
        except Exception:
            return False

    def get_account(self) -> Dict[str, Any]:
        return self._get("/fapi/v2/account", signed=True)

    def get_price(self, symbol: str) -> float:
        data = self._get("/fapi/v1/ticker/price", {"symbol": symbol})
        return float(data["price"])

    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 120) -> list:
        return self._get(
            "/fapi/v1/klines",
            {"symbol": symbol.upper(), "interval": interval, "limit": limit},
        )


class BinanceAPIError(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(f"[{code}] {msg}")
