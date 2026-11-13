#!/usr/bin/env python3
"""eth-pnl-fixed — dual-timeframe MACD crossover strategy (wallet 6).

A MACD crossover system run on 15-minute aggregated bars, not on the raw
1-minute bars. That is the whole point: on 1-minute bars MACD whipsaws
itself to death on this sample (tested: MACD 12/26/9 on 1m bars nets
about -438 USDT after costs, ~146 fills). Aggregating to 15 minutes
filters the chop and leaves 6 fills for the whole 24h window.

Signal (no lookahead — this is the part that matters):
  * 15-minute bars are built from the 1-minute closes; bar k closes at
    1-minute bar 15*k+14.
  * The position for 1-minute bar t is decided only from 15-minute bars
    that have CLOSED by the end of bar t-1. The last completed 15-minute
    bar index is b = t // 15 - 1. A 15-minute bar still in progress is
    never used: its close is a future price at decision time.
  * MACD(8, 21, 7) on those completed 15-minute closes: fast EMA(8) minus
    slow EMA(21), signal = EMA(7) of the MACD line. A cross of the MACD
    line above its signal line flips the position to long (+1 ETH); a
    cross below flips it to short (-1 ETH). The system is always in the
    market once the first cross fires (no exit-to-flat rule); a flip
    costs 2 ETH of notional (close one side, open the other).
  * Position changes take effect at the OPEN of bar t.

Why these parameters: MACD(8, 21, 7) is a faster MACD than the textbook
12/26/9, suited to a 24h window where the textbook setting reacts a
full 15-minute bar later on the two moves that matter. The choice sits
on a broad plateau, not a sharp peak: neighbouring settings on the same
no-lookahead replay score +82 to +93 USDT (12/26/9: +92.88; 8/21/5:
+91.83; 8/21/9: +85.15; 6/17/5: +91.75; 10/25/5: +82.75; 19/39/9:
+89.95), all with 4-10 fills. The 15-minute aggregation itself is the
robust part; the exact MACD lengths move the result by ~10 USDT.

Tested and REJECTED on the same bars, same cost model (honest negatives):
  * 1-minute MACD crossovers: -413 to -612 USDT (whipsaw).
  * MACD on 15m bars + 1-minute ATR trailing stop (1.5x-4x): -36 to +1
    USDT — the stop exits mid-trend and there is no fresh cross to
    re-enter on, so it gives back the trend leg.
  * VWAP mean reversion (anchored VWAP, z 0.5-2.0): -22 to -58 USDT.
  * Keltner-channel mean reversion: -170 to -414 USDT.
  * Volatility-filtered EMA trend: -52 to -168 USDT.

Usage: python3 strategy.py [bars.csv] [positions.csv]
Writes positions.csv: minute,position with position in {-1, 0, 1}.
Pure standard library. Deterministic.
"""
import csv
import sys

AGG = 15            # minutes per aggregated bar
MACD_FAST = 8
MACD_SLOW = 21
MACD_SIGNAL = 7


def read_bars(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return ([float(r["open"]) for r in rows],
            [float(r["close"]) for r in rows])


def ema(values, period):
    k = 2.0 / (period + 1)
    out = []
    v = None
    for x in values:
        v = x if v is None else x * k + v * (1.0 - k)
        out.append(v)
    return out


def positions_for(opens, closes):
    n = len(closes)
    # Completed 15-minute bars only: bar k closes at 1m bar 15*k+14.
    agg_closes = [closes[min(i + AGG - 1, n - 1)]
                  for i in range(0, n, AGG)]
    fast = ema(agg_closes, MACD_FAST)
    slow = ema(agg_closes, MACD_SLOW)
    macd = [fast[i] - slow[i] for i in range(len(agg_closes))]
    signal = ema(macd, MACD_SIGNAL)

    pos = [0] * n
    cur = 0
    for t in range(1, n):
        b = t // AGG - 1  # last 15m bar closed by end of bar t-1
        if b >= 1:
            cross_up = macd[b] > signal[b] and macd[b - 1] <= signal[b - 1]
            cross_dn = macd[b] < signal[b] and macd[b - 1] >= signal[b - 1]
            if cur == 0:
                if cross_up:
                    cur = 1
                elif cross_dn:
                    cur = -1
            elif cur == 1 and cross_dn:
                cur = -1
            elif cur == -1 and cross_up:
                cur = 1
        pos[t] = cur
    return pos


def main() -> None:
    bars_path = sys.argv[1] if len(sys.argv) > 1 else "bars.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "positions.csv"
    opens, closes = read_bars(bars_path)
    pos = positions_for(opens, closes)
    assert len(pos) == len(closes) == 1440, "expected 1440 bars"
    assert set(pos) <= {-1, 0, 1}
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["minute", "position"])
        for i, p in enumerate(pos):
            w.writerow([i, p])
    n_long = sum(1 for p in pos if p == 1)
    n_short = sum(1 for p in pos if p == -1)
    n_flat = sum(1 for p in pos if p == 0)
    print(f"wrote {out_path}: 1440 rows, long {n_long}, short {n_short}, "
          f"flat {n_flat}")


if __name__ == "__main__":
    main()
