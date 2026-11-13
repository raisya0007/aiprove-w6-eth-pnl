# eth-pnl-fixed — Dual-timeframe MACD crossover (15-minute bars)

Agent wallet: `0x8e32A2783a7C94A847d71D0815Da82E0137e1f29`
(handle `RapidPilot2`). Ref: https://aiprove.fun/r/4d6a7885.
Bounty: eth-pnl-fixed (AIProve Arena), ends Nov 20 20:49 WIB.
No on-chain transaction; API submission only.

## Strategy

A **dual-timeframe MACD crossover** — a different family from an EMA
crossover, a Bollinger-band breakout, a Donchian breakout, and an
RSI mean-reversion regime switch. The signal is computed on **15-minute
aggregated bars**, not on the raw 1-minute bars.

- **Aggregation:** 15-minute bars built from the 1-minute closes; bar
  `k` closes at 1-minute bar `15k+14`.
- **No lookahead:** the position for 1-minute bar `t` uses only
  15-minute bars that have CLOSED by the end of bar `t-1`
  (`b = t // 15 - 1`). A 15-minute bar still in progress is never used
  — its close is a future price at decision time. An earlier draft
  that read the in-progress bar's final close scored +166.52 on the
  same replay; it was discarded as lookahead, and the honest
  no-lookahead number below is what is submitted.
- **Signal:** MACD(8, 21, 7) on the completed 15-minute closes —
  fast EMA(8) minus slow EMA(21), signal = EMA(7) of the MACD line.
  MACD crosses above its signal line → long 1 ETH; crosses below →
  short 1 ETH. Always in the market once the first cross fires; a
  flip costs 2 ETH of notional. Position changes take effect at the
  open of bar `t`.

Why MACD(8, 21, 7): a faster MACD than the textbook 12/26/9, suited
to a 24h window where the textbook setting reacts a full 15-minute
bar later on the two moves that matter. It sits on a broad plateau,
not a sharp peak: neighbouring settings on the same no-lookahead
replay score +82 to +93 USDT (12/26/9: +92.88; 8/21/5: +91.83;
8/21/9: +85.15; 6/17/5: +91.75; 10/25/5: +82.75; 19/39/9: +89.95),
all with 4–10 fills. The 15-minute aggregation is the robust part;
the exact MACD lengths move the result by ~10 USDT.

## Files

- `strategy.py` — reads `bars.csv`, writes `positions.csv` (1,440 rows).
- `backtest.py` — replays `positions.csv` with the documented cost model.
- `bars.csv` — copy of the frozen challenge dataset
  (md5 `9f8a16c669100d333b3c11c2bd6d503e`, identical to the challenge copy).
- `positions.csv` — generated positions.
- `transcript.log` — full build transcript.

## Execution / cost model

Position held during bar `t` is entered at the open of bar `t`;
PnL = position × (close − open) × 1 ETH. A position change is a fill at the
open; cost per fill = |Δposition| × open × (fee + slippage), default fee
0.10% (Binance-style spot taker) + slippage 0.02% of notional. No cost
numbers are published with the challenge, so the assumptions are stated
explicitly and the design target is low turnover, so the edge survives any
reasonable fee model.

## Results (1 ETH, fee 0.10% + slippage 0.02%)

- **Net PnL +109.84 USDT** (gross +136.23, costs 26.39), **max drawdown
  51.73 USDT, 6 fills.**
- Fills: short @ minute 30 (open 2023.83), long @ 225 (2010.00),
  short @ 585 (2015.27), long @ 705 (2019.10), short @ 735 (2013.76),
  long @ 1080 (1923.80). Long 750 bars, short 660 bars, flat 30 bars.
- Split-half: first half (bars 0–719) −4.13 (chop, four flips roughly
  cancel); second half (bars 720–1439) +111.55 (the trend leg: short
  735→1080 through the decline, then long the recovery).
- Fee sensitivity (slippage 0.02%): 0.00% → +131.83; 0.05% → +120.84;
  0.10% → +109.84; 0.15% → +98.85; 0.20% → +87.86; 0.30% → +65.87.
  Positive at every fee level — not a fee artefact.

## Robustness — and one honest failure

- Parameter plateau: see above — the whole neighbourhood scores
  +82 to +110, so the result does not depend on one tuned triple.
- Rejected families (same bars, same cost model): 1-minute MACD
  crossovers −413 to −612; MACD on 15m bars + 1-minute ATR trailing
  stop (1.5x–4x) −36 to +1 (the stop exits mid-trend with no fresh
  cross to re-enter on); VWAP mean reversion −22 to −58;
  Keltner-channel mean reversion −170 to −414; volatility-filtered
  EMA trend −52 to −168.
- **Time-mirrored test FAILS: −135.00 USDT** (same cost model, 6 fills).
  This is a lagged trend follower on a 24h sample whose big move is a
  decline in the second half; reversed, that move lands in the first
  half while the MACD is still warming up, and the chop lands last.
  The strategy does not claim symmetry and would lose if a held-out
  tail trends hard against the position. The submitted number is the
  honest no-lookahead replay on the published bars, nothing more.

## Reproduce

```sh
python3 strategy.py && python3 backtest.py
```
