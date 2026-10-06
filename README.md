# Perpetual Futures Risk Calculator

![tests](https://github.com/aadirani/perp-futures-risk-calculator/actions/workflows/tests.yml/badge.svg)

Before opening a leveraged USDT perpetual futures position, this calculator tells you **how big the position should be**, **where liquidation would roughly happen**, **what fees and funding cost**, and **whether your stop-loss can even be reached**.

> Educational tool. It does arithmetic on your own plan. It doesn't connect to any exchange, doesn't place orders, and isn't investment advice.

## The idea in one paragraph

Decide how much of your account you're willing to lose if your stop is hit, for example 1%. The calculator works backwards from that to the position size, **including fees on both sides**. It then checks the leverage: if the exchange would liquidate you *before* price reaches your stop, it warns you. Leverage doesn't change how much you lose at the stop. It only changes how much margin is locked up and how close liquidation is.

## Example

Needs Python 3.9+, nothing to install.

```bash
python -m perprisk --side long --entry 60000 --stop 58800 --equity 10000 --risk-pct 1 --leverage 10 --take-profit 63600 --lot-step 0.001 --funding-rate 0.0001 --hours 24
```

```
Position size (coins)            0.079000
Position value (USDT)            4,740.00
Margin required (USDT)           474.00
Liquidation price (estimate)     54,300.00
Max leverage before stop         40.0x
Loss if stop is hit (USDT)       99.96
Loss if stop is hit (% equity)   1.00 %
Fees included in that loss       5.16
Break-even price after fees      60,066.04
Funding cost estimate (USDT)     1.42
Profit at take-profit (USDT)     279.03
Reward : risk                    2.79
```

Try the same trade with `--leverage 50`. The estimated liquidation (≈ 59,100) is then above the stop, and the tool prints a warning.

## What's inside

| Path | What it is |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Problem, design diagram, every formula with its derivation, 5 decision records, risks |
| [perprisk/calculator.py](perprisk/calculator.py) | The maths: pure functions, no network |
| [perprisk/\_\_main\_\_.py](perprisk/__main__.py) | Command-line interface |
| [tests/test_calculator.py](tests/test_calculator.py) | Each formula checked against hand-calculated numbers |
| [docs/code-walkthrough.md](docs/code-walkthrough.md) | Plain-language explanation |

## Limitations

Simplified model: isolated margin, one flat maintenance margin rate, the same fee on entry and exit. Real exchanges use tiered maintenance margin, liquidation fees and the mark price, so **always compare the liquidation estimate with your exchange's own figure**. Gaps and slippage can make a real loss bigger than planned.

