# Freqtrade EMA9 × VWAP Crossover Strategy

A high-expectancy, long-only crypto futures strategy built for [Freqtrade](https://www.freqtrade.io/). It exploits trend breakouts using an **EMA9 cross above a daily-anchored VWAP**, paired with an asymmetric **1:2 Risk/Reward ratio** derived dynamically from ATR volatility.

Included in this repository is the **full forward-test dataset of 382 live shadow trades** recorded across 139 altcoins on Gate.io futures, providing an empirical benchmark for local backtesting and hyperopt calibration.

---

## 📊 Live Forward-Test Benchmark Results

Over a 6.2-day live forward-test on 30-second live exchange tickers across 139 altcoins:

| Metric | Result (at $1.00 Margin) | Result (at $10.00 Margin) |
| :--- | :--- | :--- |
| **Total Trades Resolved** | **382** | **382** |
| **Win Rate** | **49.2%** (188 W / 190 L / 3 Liq / 1 Exp) | **49.2%** |
| **Total Net Profit** | **`+$78.34 USD`** (**+78.3R**) | **`+$783.40 USD`** |
| **Profit Factor** | **2.02** | **2.02** |
| **Average Win** | **`+$0.83 USD`** (+83% on margin) | **`+$8.30 USD`** |
| **Average Loss** | **`-$0.39 USD`** (-39% on margin) | **`-$3.90 USD`** |
| **Win/Loss Payoff Ratio** | **2.12x** (Wins out-earn losses by > 2x) | **2.12x** |
| **Average Hold Time** | **9.87 hours** | **9.87 hours** |
| **Profitable Coins** | **65.5%** (91 of 139 coins net positive) | **65.5%** |
| **Max Drawdown** | **$24.56 USD** (~29% from peak) | **$245.60 USD** |

> [!NOTE]
> All returns above **already include 0.10% round-trip exchange taker fees** and full liquidation losses.

---

## 🧠 Strategy Mechanics

### 1. Indicators & Geometry (1h Timeframe)
* **EMA9:** 9-period Exponential Moving Average on `close`.
* **Daily-Anchored VWAP:** Cumulative $\frac{\sum (Typical\ Price \times Volume)}{\sum Volume}$, strictly reset at **00:00 UTC** each day.
* **ATR14:** 14-period True Range smoothed via Exponential Moving Average ($\alpha = \frac{2}{15}$).

### 2. Two-Stage Entry Trigger
1. **ARMED:**
   * EMA9 crosses above daily-anchored VWAP on a closed 1h candle.
   * **Rule 3:** The crossover candle must close **above both** EMA9 and VWAP.
   * **Tradeability Filter:** Stop distance $\frac{1.5 \times ATR}{\text{Trigger High}} < 3.8\%$. At 20x leverage, liquidation is ~4.0%. Setups with stops $\ge 3.8\%$ are **refused** to prevent exchange liquidations.
   * Setup records the **Trigger Price** as the crossover candle's High.
2. **ENTERED:**
   * Remains armed for up to 3 candles (`ARM_BARS = 3`).
   * Enters Long when price breaks out above the Trigger High.
   * If EMA9 drops back below VWAP or 3 candles pass without a breakout, the armed state expires without risking capital.

### 3. Exits & Protections
* **Take Profit:** `Entry + (3.0 × ATR)` $\rightarrow$ **Exact 1:2 Risk/Reward ratio**.
* **Stop Loss:** `Entry - (1.5 × ATR)`, dynamically capped at 80% of the distance to the exchange liquidation price.
* **Time Expiration:** 60 hours maximum hold time (`MAX_HOLD_HOURS = 60`).
* **Protections:** 2-candle cooldown per coin, and circuit-breaker pause on repeat stop-outs.

---

## 📁 Repository Structure

```
.
├── config.json                     # Default futures configuration (Gate / Binance)
├── config.example.json             # Clean config template
├── docker-compose.yml              # Optional Docker setup
├── setup.sh                        # Automated setup script (macOS / Linux)
├── start.sh                        # Launch script for dry-run / live bot
├── data/
│   ├── vwap-shadow-trades.json     # Complete 382 forward-tested trades (JSON)
│   └── vwap-shadow-trades.csv      # Complete 382 forward-tested trades (CSV)
├── scripts/
│   ├── analyze_trades.py           # Benchmark performance & equity curve analyzer
│   └── download_data.sh            # Downloads 1h candle data for backtesting
└── user_data/
    └── strategies/
        └── EmaVwapLong.py          # Native production Freqtrade strategy implementation
```

---

## 🚀 Quickstart on Mac Mini (or Linux)

### 1. Installation
Clone the repository and run the setup script:

```bash
git clone https://github.com/xenoxavier/freqtrade-ema-vwap.git
cd freqtrade-ema-vwap
chmod +x setup.sh start.sh scripts/*.sh

# Run setup (creates .venv and installs freqtrade, talib, pandas-ta)
./setup.sh
```

*(On macOS, ensure Python 3.11+ is installed via Homebrew: `brew install python@3.12`)*

### 2. Analyze the Forward-Test Trade Dataset
Verify the benchmark statistics directly on your machine:

```bash
# Analyze at $1 margin / 20x leverage ($20 notional)
python3 scripts/analyze_trades.py --margin 1.0

# Analyze at $10 margin / 20x leverage ($200 notional)
python3 scripts/analyze_trades.py --margin 10.0
```

### 3. Run the Bot (Dry-Run Mode)
Launch the bot in dry-run mode to start monitoring signals and paper-trading live:

```bash
./start.sh
```

Access the built-in Freqtrade Web UI at **`http://127.0.0.1:8084`** (credentials generated during `./setup.sh`).

---

## 🔬 Backtesting & Improvement

### 1. Download Historical Data
Download 30 to 90 days of 1h historical futures data:

```bash
# Downloads 60 days of 1h data using config.json
./scripts/download_data.sh 60 1h
```

### 2. Run a Backtest
```bash
.venv/bin/freqtrade backtesting \
  --config config.json \
  --userdir user_data \
  --strategy EmaVwapLong \
  --timerange 20260801-20260918
```

### 3. Hyperparameter Optimization
Calibrate parameters (e.g. ATR multiplier, EMA period, arming window) to improve Sharpe ratio and reduce drawdown:

```bash
.venv/bin/freqtrade hyperopt \
  --config config.json \
  --userdir user_data \
  --strategy EmaVwapLong \
  --hyperopt-loss SharpeHyperOptLoss \
  --epochs 100
```

---

## ⚠️ Real-World Risk & Execution Guidelines

1. **Cap Max Open Trades:** During high-volatility sessions, dozens of coins can trigger breakouts simultaneously (up to 86 concurrent trades in the forward test). `config.json` sets `"max_open_trades": 8` to keep total account margin utilization controlled.
2. **Sizing & Account Cushion:**
   * At **$1 margin per trade**, maintain at least **$50–$100** in your futures account.
   * At **$10 margin per trade**, maintain at least **$500–$1,000**.
3. **Market Regime Awareness:** This is a **long-only** breakout strategy. In heavy bear trends or market-wide chops, reduce position sizing or enforce a market trend filter (e.g., BTC > 50-day EMA).

---

## 📄 License
MIT
