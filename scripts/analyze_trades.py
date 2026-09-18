#!/usr/bin/env python3
"""
analyze_trades.py - Statistical analysis of forward-tested EMA9 x VWAP shadow trades.

Usage:
    python3 scripts/analyze_trades.py
    python3 scripts/analyze_trades.py --margin 1.0
    python3 scripts/analyze_trades.py --margin 10.0
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter


def analyze(data_path: str, margin: float = 1.0, leverage: float = 20.0):
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        sys.exit(1)

    with open(data_path, "r") as f:
        trades = json.load(f)

    if not trades:
        print("No trades found.")
        return

    total = len(trades)
    wins = [t for t in trades if t.get("status") == "target"]
    losses = [t for t in trades if t.get("status") == "stopped"]
    liqs = [t for t in trades if t.get("status") == "liquidated"]
    expired = [t for t in trades if t.get("status") == "expired"]

    # Calculate PnL based on specified margin
    for t in trades:
        pnl_pct_margin = t.get("pnlPctOfMargin", 0.0)
        t["calc_pnl_usd"] = margin * (pnl_pct_margin / 100.0)

    total_pnl = sum(t["calc_pnl_usd"] for t in trades)
    gross_win = sum(t["calc_pnl_usd"] for t in wins)
    gross_loss = abs(sum(t["calc_pnl_usd"] for t in losses + liqs))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

    win_rate = (len(wins) / total) * 100

    avg_win = (gross_win / len(wins)) if wins else 0
    avg_loss = (sum(t["calc_pnl_usd"] for t in losses) / len(losses)) if losses else 0
    avg_trade = total_pnl / total

    # Duration
    durations = [t.get("hoursHeld", 0) for t in trades if "hoursHeld" in t]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Drawdown calculation
    sorted_trades = sorted(trades, key=lambda x: x.get("closedAt", 0))
    cum = 0
    peak = 0
    max_dd = 0
    for t in sorted_trades:
        cum += t["calc_pnl_usd"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    # Max concurrent open positions
    events = []
    for t in trades:
        if t.get("enteredAt") and t.get("closedAt"):
            events.append((t["enteredAt"], 1))
            events.append((t["closedAt"], -1))
    events.sort(key=lambda x: x[0])
    curr = 0
    max_concurrent = 0
    for _, delta in events:
        curr += delta
        if curr > max_concurrent:
            max_concurrent = curr

    # Coin breakdown
    by_coin = {}
    for t in trades:
        c = t.get("base", "UNKNOWN")
        by_coin[c] = by_coin.get(c, 0.0) + t["calc_pnl_usd"]

    sorted_coins = sorted(by_coin.items(), key=lambda x: x[1], reverse=True)
    profitable_coins = [c for c in sorted_coins if c[1] > 0]

    # Date range
    first_time = sorted_trades[0].get("entered_at_utc", "N/A")
    last_time = sorted_trades[-1].get("closed_at_utc", "N/A")

    print("\n" + "=" * 65)
    print(f"   EMA9 x VWAP SHADOW PERFORMANCE REPORT")
    print(f"   Sizing: ${margin:.2f} Margin | {leverage:.0f}x Leverage | Notional: ${margin * leverage:.2f}/trade")
    print("=" * 65)
    print(f"Date Range:          {first_time}  ->  {last_time}")
    print(f"Total Trades:        {total}")
    print(f"Win Rate:            {win_rate:.1f}% ({len(wins)} wins, {len(losses)} losses, {len(liqs)} liqs, {len(expired)} expired)")
    print(f"Total Net P&L:       ${total_pnl:+.2f} USD")
    print(f"Profit Factor:       {profit_factor:.2f}")
    print(f"Average Trade:       ${avg_trade:+.3f} USD")
    print(f"Average Win:         ${avg_win:+.2f} USD")
    print(f"Average Loss:        ${avg_loss:+.2f} USD")
    print(f"Win/Loss Payoff:     {abs(avg_win / avg_loss):.2f}x (Risk/Reward 1:2)")
    print(f"Average Hold Time:   {avg_duration:.2f} hours")
    print(f"Max Drawdown:        ${max_dd:.2f} USD")
    print(f"Max Concurrent Open: {max_concurrent} trades (Peak margin needed: ${max_concurrent * margin:.2f})")
    print("-" * 65)
    print(f"Coins Traded:        {len(sorted_coins)} unique coins")
    print(f"Profitable Coins:    {len(profitable_coins)} / {len(sorted_coins)} ({len(profitable_coins)/len(sorted_coins)*100:.1f}%)")
    print("\nTop 5 Earning Coins:")
    for c, p in sorted_coins[:5]:
        share = (p / total_pnl * 100) if total_pnl > 0 else 0
        print(f"  {c:<10} ${p:>8.2f} ({share:4.1f}% of total)")
    print("\nWorst 5 Coins:")
    for c, p in sorted_coins[-5:]:
        print(f"  {c:<10} ${p:>8.2f}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze EMA9 x VWAP shadow trades")
    parser.add_argument("--margin", type=float, default=1.0, help="Margin per trade in USD (default: 1.0)")
    parser.add_argument("--leverage", type=float, default=20.0, help="Leverage multiplier (default: 20.0)")
    parser.add_argument("--file", type=str, default="data/vwap-shadow-trades.json", help="Path to trade JSON file")
    args = parser.parse_args()

    # resolve relative file path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, args.file) if not os.path.isabs(args.file) else args.file

    analyze(target_path, margin=args.margin, leverage=args.leverage)
