# 🤖 Binance Futures Testnet Trading Bot

A clean, structured Python CLI trading bot for **Binance Futures Testnet (USDT-M Perpetuals)**.

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST API wrapper (signing, requests, error handling)
│   ├── orders.py          # Order placement logic + output formatting
│   ├── validators.py      # Input validation (symbol, side, qty, price)
│   └── logging_config.py  # Structured file + console logging
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   ├── market_order_sample.log
│   └── limit_order_sample.log
├── .env.example
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/your-username/trading_bot.git
cd trading_bot
pip install -r requirements.txt
```

### 2. Get Testnet API credentials

1. Go to [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in and navigate to **Settings → API Configuration**
3. Generate your API Key and Secret

### 3. Set environment variables

```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

Or copy `.env.example` to `.env` and fill in values (requires `python-dotenv`).

---

## 🚀 How to Run

### Place a MARKET order
```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --qty 0.01
```

### Place a LIMIT order
```bash
python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --qty 0.5 --price 3500.00
```

### Place a STOP_MARKET order (bonus)
```bash
python cli.py order --symbol SOLUSDT --side SELL --type STOP_MARKET --qty 10 --stop-price 130.00
```

### Check current price
```bash
python cli.py price --symbol BTCUSDT
```

### View account balances
```bash
python cli.py account
```

### List open orders
```bash
python cli.py open-orders --symbol ETHUSDT
```

---

## 📋 CLI Reference

| Argument | Description | Required |
|----------|-------------|----------|
| `--symbol` | Trading pair (e.g. BTCUSDT) | ✅ |
| `--side` | BUY or SELL | ✅ |
| `--type` | MARKET / LIMIT / STOP / STOP_MARKET | ✅ |
| `--qty` | Order quantity | ✅ |
| `--price` | Limit/stop price | For LIMIT/STOP |
| `--stop-price` | Stop trigger price | For STOP/STOP_MARKET |
| `--tif` | Time-in-force: GTC, IOC, FOK (default: GTC) | ❌ |

---

## 📦 Assumptions

- Only USDT-M Perpetual Futures (not COIN-M)
- All orders placed on **Testnet** (`https://testnet.binancefuture.com`)
- Symbols validated against a curated set of popular pairs; extend `VALID_SYMBOLS` in `validators.py` as needed
- Logs rotate daily in `logs/trading_bot_YYYYMMDD.log`
- No position/margin management — raw order placement only

---

## 🏆 Bonus Features Implemented

- ✅ **STOP_MARKET / STOP** order type (3rd order type)
- ✅ **Colour-coded terminal output** with ASCII art banner
- ✅ **Structured logging** (debug to file, info to console)

---

## 📝 Log Files

Sample logs included:
- `logs/market_order_sample.log` — BTCUSDT MARKET BUY, status FILLED
- `logs/limit_order_sample.log` — ETHUSDT LIMIT SELL, status NEW → CANCELED

---

## 🌐 Web UI (Bonus)

A fully functional browser interface is included. It connects to a FastAPI backend that talks to Binance Testnet in real time.

### Start the server

```bash
pip install -r requirements.txt

export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

uvicorn server:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

### What the UI does (all real, live data):
- Fetches your **live testnet balance** on load
- Shows **live prices** for BTC, ETH, SOL (refreshes every 5s)
- Places **real orders** on testnet when you click Buy/Long or Sell/Short
- Shows a **result modal** with orderId, status, executedQty, avgPrice
- Displays your **open orders** for the selected symbol
- **Live log stream** at the bottom for every API call
- Shows the **CLI equivalent command** as you fill the form

### API endpoints (also usable directly):
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ping` | Test connection |
| GET | `/api/price/{symbol}` | Live mark price |
| GET | `/api/account` | Balance & PnL |
| POST | `/api/order` | Place order |
| GET | `/api/open-orders` | List open orders |
