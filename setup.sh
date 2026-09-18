#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=========================================================="
echo "   Freqtrade EMA9 x VWAP Setup (Mac Mini / Linux)"
echo "=========================================================="

command -v python3 >/dev/null || { echo "Install Python first: brew install python@3.12 (macOS) or apt install python3-venv"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
  || { echo "Need Python 3.10+. Run: brew install python@3.12"; exit 1; }

echo "1. Creating Python virtual environment in .venv..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip setuptools wheel -q

echo "2. Installing Freqtrade & technical analysis libraries (takes 2-3 mins)..."
.venv/bin/pip install freqtrade pandas-ta technical -q

echo "3. Initializing local config & generating secure UI credentials..."
python3 - <<'PY'
import json, secrets, pathlib, shutil

cfg_path = pathlib.Path('config.json')
example_path = pathlib.Path('config.example.json')

if not cfg_path.exists() and example_path.exists():
    shutil.copy('config.example.json', 'config.json')

if cfg_path.exists():
    c = json.loads(cfg_path.read_text())
    if 'api_server' in c:
        c['api_server']['jwt_secret_key'] = secrets.token_hex(32)
        c['api_server']['ws_token'] = secrets.token_urlsafe(32)
        c['api_server']['password'] = secrets.token_urlsafe(18)
        cfg_path.write_text(json.dumps(c, indent=4))
        print("   ✓ config.json generated with local secrets")
        print("   Web UI URL: http://127.0.0.1:" + str(c['api_server'].get('listen_port', 8084)))
        print("   Username  : " + c['api_server']['username'])
        print("   Password  : " + c['api_server']['password'])
PY
chmod 600 config.json 2>/dev/null || true

echo "4. Verifying strategy compilation..."
.venv/bin/python3 -c "
import sys
sys.path.append('user_data/strategies')
from EmaVwapLong import EmaVwapLong
s = EmaVwapLong({})
print('   ✓ EmaVwapLong strategy verified successfully')
"

echo
echo "Setup complete! Next steps:"
echo "  * To analyze the forward-test benchmark trades: python3 scripts/analyze_trades.py"
echo "  * To run dry-run trading:                       ./start.sh"
echo "  * To download data and backtest:                ./scripts/download_data.sh"
echo "=========================================================="
