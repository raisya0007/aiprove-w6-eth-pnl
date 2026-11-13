#!/usr/bin/env python3
"""Replay positions.csv over bars.csv and report net PnL after costs.

Execution model (documented, no phantom fills)
----------------------------------------------
- The position listed for minute t is the position HELD during bar t. It was
  decided from bars up to t-1 (see strategy.py), and is entered at the OPEN
  of bar t. Bar t PnL = position[t] * (close[t] - open[t]) * 1 ETH.
- A change in position is a fill at the open price of bar t. Cost per fill:
  fee + slippage, charged on the notional that changed hands:
      cost = |position[t] - position[t-1]| * open[t] * (fee + slippage)
  Default: fee = 0.10% (Binance-style spot taker), slippage = 0.02% of
  notional. Size is fixed at 1 ETH, so slippage stays small.
- Max drawdown is measured on the running net-PnL equity curve (peak to
  trough, in USDT). Trade count = number of fills (position changes).
- Pure standard library: no third-party dependency. Deterministic.

Sensitivity: --fee / --slippage run the same replay at other cost levels.
Usage:  python3 backtest.py [bars.csv] [positions.csv] [--fee 0.001]
"""
import argparse
import csv


DEFAULT_FEE = 0.001         # 0.10% per fill
DEFAULT_SLIPPAGE = 0.0002   # 0.02% of notional


def replay(bars, pos, fee=DEFAULT_FEE, slippage=DEFAULT_SLIPPAGE):
    pnl = 0.0
    peak = 0.0
    max_dd = 0.0
    trades = 0
    gross = 0.0
    costs = 0.0
    prev = 0
    for (minute, op, cl), p in zip(bars, pos):
        if p != prev:
            trades += 1
            c = abs(p - prev) * op * (fee + slippage)
            pnl -= c
            costs += c
        g = p * (cl - op)
        pnl += g
        gross += g
        peak = max(peak, pnl)
        max_dd = max(max_dd, peak - pnl)
        prev = p
    return {"net_pnl": pnl, "gross_pnl": gross, "costs": costs,
            "max_drawdown": max_dd, "trades": trades}


def fills(bars, pos):
    out = []
    prev = 0
    for (minute, op, cl), p in zip(bars, pos):
        if p != prev:
            out.append((minute, prev, p, op))
            prev = p
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("bars", nargs="?", default="bars.csv")
    ap.add_argument("positions", nargs="?", default="positions.csv")
    ap.add_argument("--fee", type=float, default=DEFAULT_FEE)
    ap.add_argument("--slippage", type=float, default=DEFAULT_SLIPPAGE)
    args = ap.parse_args()
    with open(args.bars, newline="") as f:
        bars = [(int(r["minute"]), float(r["open"]), float(r["close"]))
                for r in csv.DictReader(f)]
    with open(args.positions, newline="") as f:
        pos = [int(r["position"]) for r in csv.DictReader(f)]
    assert len(bars) == len(pos), "bars/positions length mismatch"
    assert set(pos) <= {-1, 0, 1}, "positions must be in {-1,0,1}"
    r = replay(bars, pos, args.fee, args.slippage)
    print(f"fee={args.fee * 100:.2f}% slippage={args.slippage * 100:.2f}% "
          f"-> net PnL={r['net_pnl']:.2f} USDT  gross={r['gross_pnl']:.2f}  "
          f"costs={r['costs']:.2f}  max DD={r['max_drawdown']:.2f}  "
          f"fills={r['trades']}")
    for minute, frm, to, op in fills(bars, pos):
        print(f"  fill @ minute {minute}: {frm:+d} -> {to:+d} @ open {op:.2f}")


if __name__ == "__main__":
    main()
