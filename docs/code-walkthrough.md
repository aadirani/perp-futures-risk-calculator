# Code walkthrough

A plain-language guide for explaining this project in an interview.

## Vocabulary in 30 seconds

- **Perpetual future ("perp"):** a contract that tracks a coin's price with no expiry date. You can go **long** (profit if price rises) or **short** (profit if it falls).
- **Leverage:** controlling a position bigger than your deposit. At 10x, $474 of margin controls a $4,740 position.
- **Margin:** the deposit locked for the position.
- **Maintenance margin rate (MMR):** the minimum margin, as a % of the position value, that must remain. Below it, the exchange **liquidates** (force-closes) the position.
- **Funding:** a payment between longs and shorts every 8 hours that keeps the perp price close to the spot price.

## `perprisk/calculator.py`

**`Trade`** is a `@dataclass` that holds all the inputs. `__post_init__` rejects impossible input straight away: a long with its stop *above* entry, a negative price, zero leverage.

**`position_size(trade)`** is the heart of the tool:
1. risk budget = equity × risk% → 10,000 × 1% = **$100**
2. loss per coin if the stop is hit = price move + entry fee + exit fee = 1,200 + 0.00055 × (60,000 + 58,800) = **1,265.34**
3. size = 100 ÷ 1,265.34 = **0.0790 coins**
4. if a lot step is given (e.g. 0.001), round **down** → 0.079, so the real risk is never above $100

**`liquidation_price(side, entry, leverage, mmr)`**: for a long, the margin is 1/L of the position, and the exchange liquidates when the loss has eaten everything except the maintenance margin. So the price can fall by (1/L − MMR) before liquidation: 60,000 × (1 − 0.10 + 0.005) = **54,300**. A short is the mirror image.

**`max_leverage_before_stop`** solves "liquidation price = stop price" for leverage. Here that's **40x**. Above it, the stop is useless because liquidation comes first.

**`breakeven_price`**: you pay a fee on the way in and on the way out, so price must move a little in your favor just to get back to zero: 60,000 × 1.00055 ÷ 0.99945 ≈ **60,066**.

**`pnl_at`** is profit or loss at any exit price, after both fees. The tests use it to *prove* other functions. For example, profit at the break-even price must be exactly 0.

**`analyze(trade)`** calls all of the above, adds funding (`position value × rate × hours ÷ 8`, positive = longs pay) and reward:risk if a take-profit is given, and collects **warnings**: liquidation before the stop, margin bigger than the account, or a position that rounds down to zero.

## `perprisk/__main__.py`

Reads the command-line options with `argparse`, builds a `Trade`, calls `analyze()`, and prints each result with a readable label. All the maths lives in `calculator.py`, so a web page or spreadsheet could reuse it unchanged. That separation is the main design choice (ADR-004).

## The tests

Each formula is checked against numbers worked out by hand: liquidation 54,300 (long) and 65,700 (short), max leverage 40x, the size formula, a loss at the stop of exactly $100, rounding down to 0.079, the 50x warning, the direction of funding payments, and rejection of bad inputs.

## Likely interview questions

- **"Does higher leverage mean higher risk?"** Not by itself. With a fixed stop and a size worked out from risk, the loss at the stop is the same at 5x or 20x. Higher leverage moves liquidation closer and can put it *before* the stop. That's the real danger, and the tool flags it.
- **"Why is your liquidation price different from the exchange's?"** Simplified model: flat MMR, no liquidation fee, no tiers, last price instead of mark price (ADR-001). That's why it's labelled an estimate.
- **"Why include fees in the size?"** Without them, a "1%" trade loses more than 1%. Here fees are about 5% of the loss at the stop (ADR-002).
- **"Can the loss be bigger than planned?"** Yes. Gaps and slippage can fill a stop at a worse price. The tool states this limitation.
