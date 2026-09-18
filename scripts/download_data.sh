#!/bin/bash
set -e
cd "$(dirname "$0")/.."

DAYS="${1:-30}"
TIMEFRAME="${2:-1h}"
CONFIG="${3:-config.json}"

if [ ! -d ".venv" ]; then
    echo "Virtualenv not found. Run ./setup.sh first."
    exit 1
fi

echo "=========================================================="
echo " Downloading $DAYS days of $TIMEFRAME candle data for backtesting"
echo "=========================================================="

.venv/bin/freqtrade download-data \
    --config "$CONFIG" \
    --userdir user_data \
    --timeframes "$TIMEFRAME" \
    --days "$DAYS"

echo
echo "Data download finished! You can now run a backtest:"
echo "  .venv/bin/freqtrade backtesting --config $CONFIG --userdir user_data --strategy EmaVwapLong"
echo "=========================================================="
