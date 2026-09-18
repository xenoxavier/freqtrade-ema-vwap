<div align="center">

# 📈 Freqtrade EMA9 × VWAP — Asymmetric 1:2 R:R Long Strategy

**A high-expectancy, 1h crypto futures breakout strategy for Freqtrade engineered with daily-anchored VWAP, ATR volatility-based stops/targets, and an empirical dataset of 382 live forward-tested trades.**

_Asymmetric 1:2 Risk/Reward payoff, 2-stage armed breakout execution, liquidation protection pre-filters, and multi-coin benchmark performance across 139 altcoins._

![status](https://img.shields.io/badge/status-verified-brightgreen?style=for-the-badge)
![timeframe](https://img.shields.io/badge/timeframe-1h-blue?style=for-the-badge)
![win-rate](https://img.shields.io/badge/win%20rate-49.2%25-orange?style=for-the-badge)
![profit-factor](https://img.shields.io/badge/profit%20factor-2.02-success?style=for-the-badge)
![rr-ratio](https://img.shields.io/badge/risk%2Freward-1%3A2-purple?style=for-the-badge)
![license](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/richardcuyk)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/richardcuyk)

[Overview](#-overview) ·
[Quick Start](#-quick-start) ·
[Live Benchmark](#-live-forward-test-benchmark) ·
[Key Capabilities](#-key-capabilities) ·
[Strategy Mechanics](#-strategy-mechanics--geometry) ·
[Repository Structure](#-repository-structure) ·
[Backtesting & Hyperopt](#-backtesting--hyperopt) ·
[Risk Management](#-risk-management--caveats) ·
[Support](#-support--donations) ·
[License](#-license)

</div>

* * *

> **Why this strategy exists:** Most retail trading strategies chase arbitrary win rates with tight 1:1 or negative risk/reward ratios that inevitably crumble under exchange fees and sudden drawdowns. This strategy does the reverse: it accepts a ~50% coin-flip win rate but mathematically enforces a **strict 1:2 Risk-to-Reward ratio** ($3.0 \times \text{ATR}$ target vs $1.5 \times \text{ATR}$ stop) combined with a **2-stage breakout confirmation**. Because winners out-earn losers by more than 2-to-1, the strategy requires only a **33.3% win rate to break even**, generating massive positive expectancy over large sample sizes.

* * *

## ✨ Overview

`EmaVwapLong` is a production-grade algorithmic trading strategy built for [Freqtrade](https://www.freqtrade.io/). It detects early momentum shifts when a short-term trend (**EMA9**) crosses above the institutional benchmark volume level (**Daily-Anchored VWAP**) and enters only when price confirms the breakout above the high of the crossover candle.

```
+------------------------------------------------------------------------------------+
|  FREQTRADE EMA9 x DAILY-ANCHORED VWAP STRATEGY PIPELINE                            |
|  +------------------------------------------------------------------------------+  |
|  | 1. CANDLE CLOSE (1h) :  EMA9 crosses above Daily VWAP (reset at 00:00 UTC)   |  |
|  +------------------------------------------------------------------------------+  |
|  | 2. RULE 3 VALIDATION :  Close must be ABOVE both EMA9 and VWAP               |  |
|  +------------------------------------------------------------------------------+  |
|  | 3. LIQ PRE-FILTER    :  Stop (1.5x ATR) must be < 3.8% (avoids 20x liq move) |  |
|  +------------------------------------------------------------------------------+  |
|  | 4. ARMED WINDOW      :  Trigger set to Cross High • Armed for up to 3 bars   |  |
|  +------------------------------------------------------------------------------+  |
|  | 5. BREAKOUT ENTRY    :  Price trades through Trigger High -> Enter Long      |  |
|  +------------------------------------------------------------------------------+  |
|  | 6. ASYMMETRIC EXIT   :  Target (+3.0x ATR)  |  Stop (-1.5x ATR)  |  60h Max  |  |
+------------------------------------------------------------------------------------+
```

---

## 🚀 Quick Start

### 1. Prerequisites
* **macOS (Mac Mini / Apple Silicon)**: Ensure Python 3.11+ is installed (`brew install python@3.12`)
* **Linux / Ubuntu**: Standard Python 3.10+ virtual environment tools (`apt install python3-venv python3-pip`)

### 2. Automated Setup (One-Click)

Clone the repository and run the setup script:

```bash
git clone https://github.com/xenoxavier/freqtrade-ema-vwap.git
cd freqtrade-ema-vwap
chmod +x setup.sh start.sh scripts/*.sh

# Run setup (creates .venv, installs freqtrade, technical, talib, pandas-ta)
./setup.sh
```

`setup.sh` automatically:
1. Provisions a dedicated Python virtual environment (`.venv`).
2. Installs Freqtrade and all technical analysis dependencies.
3. Automatically generates secure local credentials and creates your private `config.json`.
4. Compiles and verifies the `EmaVwapLong` strategy.

### 3. Verify the Forward-Test Benchmark
Analyze the 382 included live forward-test trades right from your terminal:

```bash
# Sized at $1 margin / 20x leverage ($20 notional/trade):
python3 scripts/analyze_trades.py --margin 1.0

# Sized at $10 margin / 20x leverage ($200 notional/trade):
python3 scripts/analyze_trades.py --margin 10.0
```

### 4. Launch the Bot (Dry-Run Mode)
```bash
./start.sh
```
Access the built-in Freqtrade Web UI at: **[http://127.0.0.1:8084](http://127.0.0.1:8084)**

---

## 📊 Live Forward-Test Benchmark

Over a 6.2-day live forward test tracked across live 30-second exchange tickers on Gate.io futures (139 altcoins):

| Metric | Result (at $1.00 Margin / 20x) | Result (at $10.00 Margin / 20x) | Strategic Meaning |
| :--- | :--- | :--- | :--- |
| **Total Trades** | **382** | **382** | High sample size across full market universe |
| **Win Rate** | **49.2%** (188 W / 190 L) | **49.2%** | Near 50/50 balance; edge comes from payoff size |
| **Net P&L** | **`+$78.34 USD`** (**+78.3R**) | **`+$783.40 USD`** | **Includes 0.10% taker fees & liquidations** |
| **Profit Factor** | **2.02** | **2.02** | Generates \$2.02 in gross profit for every \$1.00 lost |
| **Average Win** | **`+$0.83 USD`** (+83% margin) | **`+$8.30 USD`** | Average gain on target hit |
| **Average Loss** | **`-$0.39 USD`** (-39% margin) | **`-$3.90 USD`** | Controlled loss on stop out |
| **Win/Loss Payoff** | **2.12x** | **2.12x** | Winners consistently out-earn losers by > 2x |
| **Average Hold Time**| **9.87 hours** | **9.87 hours** | Swing horizon; avoids high-frequency fee drag |
| **Profitable Coins** | **65.5%** (91 of 139 coins) | **65.5%** | Edge is market-wide, not driven by 1 lucky meme pump |
| **Max Drawdown** | **$24.56 USD** (~29% from peak)| **$245.60 USD** | Manageable peak-to-trough pullback |

---

## 🎯 Key Capabilities

| Feature | Implementation | Trading Advantage |
| :--- | :--- | :--- |
| **Daily-Anchored VWAP** | Resets strictly at 00:00 UTC daily | Prevents VWAP flattening into an unresponsive moving average over weeks |
| **2-Stage Breakout Filter** | Armed on cross $\rightarrow$ entered on high break | Eliminates false crossovers that immediately roll over (136 false breaks skipped) |
| **Asymmetric 1:2 R:R** | $1.5 \times \text{ATR}$ stop / $3.0 \times \text{ATR}$ target | Positive expectancy even if win rate drops as low as 35% |
| **Liquidation Pre-Filter** | Max Stop $< 3.8\%$ filter | Rejects setups where stop would lie beyond 20x liquidation (~4.0%) |
| **Liquidation Safety Cap** | `LIQ_SAFETY = 0.80` | Dynamically caps stop inside liquidation price to ensure stop order always fires |
| **Time-Decay Stop** | 60-hour max hold timeout | Frees locked margin from stagnant, low-volatility chop |
| **Tag State Persistence** | Encoded `enter_tag` parameters | Preserves exact entry ATR levels and stops across bot reboots |

---

## 📐 Strategy Mechanics & Geometry

### 1. Indicators
* **EMA9**: Exponential Moving Average over 9 periods on hourly `close`.
* **Daily Anchored VWAP**:
  $$\text{Typical Price } (TP) = \frac{\text{High} + \text{Low} + \text{Close}}{3}$$
  $$\text{VWAP} = \frac{\sum (TP \times \text{Volume})}{\sum \text{Volume}} \quad \text{(reset daily at 00:00 UTC)}$$
* **ATR14**: Exponential True Range smoothing with span 14 ($\alpha = \frac{2}{15}$).

### 2. The Setup Trigger
1. **Cross**: `EMA9 > VWAP` on candle $t$, and `EMA9 <= VWAP` on candle $t-1$.
2. **Rule 3**: Candle must close above both lines: `Close > EMA9` and `Close > VWAP`.
3. **Volatility Filter**:
   $$\text{Stop \%} = \frac{1.5 \times \text{ATR}}{\text{Trigger High}} \times 100 < 3.8\%$$
4. **Arming**: Trigger is set to $\text{High}_{\text{cross}}$. Setup stays armed for up to 3 bars as long as EMA9 remains above VWAP.
5. **Entry**: Executes when price trades through the Trigger High.

### 3. Exits
* **Take Profit:** $\text{Entry} + (3.0 \times \text{ATR})$
* **Stop Loss:** $\text{Entry} - (1.5 \times \text{ATR})$
* **Timeout:** Closed at market after 60 hours.

---

## 📁 Repository Structure

```
freqtrade-ema-vwap/
├── README.md                      # Comprehensive documentation & reference
├── setup.sh                       # 1-click installation script (macOS / Linux)
├── start.sh                       # Bot runner script (dry-run & live)
├── config.example.json            # Clean template config with API placeholders
├── docker-compose.yml             # Containerized deployment setup
├── data/
│   ├── vwap-shadow-trades.json    # Complete 382 forward-test trades in JSON
│   └── vwap-shadow-trades.csv     # Complete 382 forward-test trades in CSV
├── scripts/
│   ├── analyze_trades.py          # Benchmark analyzer & equity curve reporter
│   └── download_data.sh           # Historical 1h futures data downloader
└── user_data/
    └── strategies/
        └── EmaVwapLong.py         # Production Freqtrade strategy implementation
```

---

## 🔬 Backtesting & Hyperopt

### 1. Download Historical Candle Data
Download 30 to 90 days of 1h historical futures data:

```bash
./scripts/download_data.sh 60 1h
```

### 2. Execute a Backtest
```bash
.venv/bin/freqtrade backtesting \
  --config config.json \
  --userdir user_data \
  --strategy EmaVwapLong \
  --timerange 20260801-20260918
```

### 3. Hyperparameter Optimization
Calibrate parameters (e.g. ATR multipliers, EMA period, arming duration) to maximize the Sharpe ratio:

```bash
.venv/bin/freqtrade hyperopt \
  --config config.json \
  --userdir user_data \
  --strategy EmaVwapLong \
  --hyperopt-loss SharpeHyperOptLoss \
  --epochs 100
```

---

## ⚠️ Risk Management & Caveats

1. **Cap Max Open Trades:** In heavy market breakouts, up to 86 coins can trigger simultaneously. `config.json` sets `"max_open_trades": 8` to safeguard total account margin.
2. **Capital Buffer:**
   * At **$1 margin per trade**, maintain at least **$50–$100** in your futures wallet.
   * At **$10 margin per trade**, maintain at least **$500–$1,000**.
3. **Market Regime Bias:** This is a **long-only** breakout strategy. In severe multi-week bear trends, reduce position sizing or integrate a macro market filter (e.g. BTC > 50-day EMA).

---

## ☕ Support & Donations

If this strategy or dataset helped you improve your trading systems, consider supporting ongoing research and open-source tooling:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://www.buymeacoffee.com/richardcuyk)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/richardcuyk)

---

## 📄 License
Released under the [MIT License](LICENSE).
