#!/bin/bash
cd "$(dirname "$0")"

STRATEGY="${1:-EmaVwapLong}"
CONFIG="${2:-config.json}"

if [ ! -d ".venv" ]; then
    echo "Virtualenv not found. Please run ./setup.sh first."
    exit 1
fi

IS_DRY=$(grep -o '"dry_run"[[:space:]]*:[[:space:]]*[a-zA-Z]*' "$CONFIG" | grep -o 'true\|false')
if [ "$IS_DRY" = "true" ]; then
    MODE="[DRY-RUN]"
else
    MODE="[*** LIVE TRADING ***]"
fi

echo "=========================================================="
echo " Starting Freqtrade: $STRATEGY $MODE"
echo " Config: $CONFIG"
echo "=========================================================="

exec .venv/bin/freqtrade trade \
    --config "$CONFIG" \
    --userdir user_data \
    --strategy "$STRATEGY"
