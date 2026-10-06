"""Risk maths for a single USDT-margined (linear) perpetual futures position.

Simplified model: isolated margin, one flat maintenance margin rate, and the
same fee rate on entry and exit. Real exchanges add tiered maintenance
margin, liquidation fees and mark-price rules, so treat the liquidation
price as an estimate and always compare it with the exchange's own figure.

Educational tool only. It does not connect to any exchange and is not
investment advice.
"""

import math
from dataclasses import dataclass, field


@dataclass
class Trade:
    side: str                    # "long" or "short"
    entry: float                 # entry price
    stop: float                  # stop-loss price
    equity: float                # account equity in USDT
    risk_pct: float              # % of equity you accept losing if the stop is hit
    leverage: float              # e.g. 10 for 10x
    fee_rate: float = 0.00055    # taker fee per side (0.055 %); check your own fee tier
    mmr: float = 0.005           # maintenance margin rate (0.5 %); varies by symbol and size
    lot_step: float = 0.0        # smallest quantity increment, e.g. 0.001 BTC; 0 = no rounding
    take_profit: float = None
    funding_rate: float = 0.0    # per 8-hour period, e.g. 0.0001 = 0.01 %
    holding_hours: float = 0.0

    def __post_init__(self):
        if self.side not in ("long", "short"):
            raise ValueError("side must be 'long' or 'short'")
        if min(self.entry, self.stop, self.equity, self.risk_pct, self.leverage) <= 0:
            raise ValueError("prices, equity, risk and leverage must be positive")
        if self.side == "long" and self.stop >= self.entry:
            raise ValueError("a long's stop must be below the entry price")
        if self.side == "short" and self.stop <= self.entry:
            raise ValueError("a short's stop must be above the entry price")


def liquidation_price(side, entry, leverage, mmr):
    """Price at which the margin left equals the maintenance margin (isolated, fees ignored).

    Long:  entry x (1 - 1/leverage + mmr)
    Short: entry x (1 + 1/leverage - mmr)
    """
    if side == "long":
        return entry * (1 - 1 / leverage + mmr)
    return entry * (1 + 1 / leverage - mmr)


def max_leverage_before_stop(side, entry, stop, mmr):
    """Highest leverage whose estimated liquidation price is still beyond the stop."""
    if side == "long":
        gap = 1 + mmr - stop / entry
    else:
        gap = stop / entry - 1 + mmr
    return math.inf if gap <= 0 else 1 / gap


def breakeven_price(side, entry, fee_rate):
    """Exit price where the trade covers its entry and exit fees exactly."""
    if side == "long":
        return entry * (1 + fee_rate) / (1 - fee_rate)
    return entry * (1 - fee_rate) / (1 + fee_rate)


def pnl_at(side, entry, exit_price, qty, fee_rate):
    """Net profit or loss in USDT after entry and exit fees."""
    direction = 1 if side == "long" else -1
    gross = direction * (exit_price - entry) * qty
    fees = fee_rate * qty * (entry + exit_price)
    return gross - fees


def position_size(trade: Trade):
    """Quantity so that hitting the stop loses about risk_pct of equity, fees included."""
    risk_amount = trade.equity * trade.risk_pct / 100
    loss_per_unit = abs(trade.entry - trade.stop) + trade.fee_rate * (trade.entry + trade.stop)
    qty = risk_amount / loss_per_unit
    if trade.lot_step > 0:
        # Round DOWN so actual risk never exceeds the target.
        qty = math.floor(qty / trade.lot_step + 1e-9) * trade.lot_step
    return qty


def analyze(trade: Trade):
    """Return a dict with the full risk picture and a list of warnings."""
    qty = position_size(trade)
    notional = qty * trade.entry
    margin = notional / trade.leverage
    liq = liquidation_price(trade.side, trade.entry, trade.leverage, trade.mmr)
    loss_at_stop = -pnl_at(trade.side, trade.entry, trade.stop, qty, trade.fee_rate)

    # Positive funding rate: longs pay shorts. Negative: shorts pay longs.
    periods = trade.holding_hours / 8
    funding_cost = notional * trade.funding_rate * periods * (1 if trade.side == "long" else -1)

    result = {
        "quantity": qty,
        "notional_usdt": notional,
        "initial_margin_usdt": margin,
        "liquidation_price_est": liq,
        "max_leverage_before_stop": max_leverage_before_stop(trade.side, trade.entry, trade.stop, trade.mmr),
        "loss_at_stop_usdt": loss_at_stop,
        "loss_at_stop_pct_equity": 100 * loss_at_stop / trade.equity,
        "breakeven_price": breakeven_price(trade.side, trade.entry, trade.fee_rate),
        "entry_plus_exit_fees_at_stop": trade.fee_rate * qty * (trade.entry + trade.stop),
        "funding_cost_est_usdt": funding_cost,
        "warnings": [],
    }

    if trade.take_profit is not None:
        reward = pnl_at(trade.side, trade.entry, trade.take_profit, qty, trade.fee_rate)
        result["profit_at_target_usdt"] = reward
        result["reward_to_risk"] = reward / loss_at_stop if loss_at_stop > 0 else None

    w = result["warnings"]
    stop_beyond_liq = trade.stop <= liq if trade.side == "long" else trade.stop >= liq
    if stop_beyond_liq:
        w.append("Estimated liquidation comes BEFORE the stop: the stop would never be reached. "
                 "Lower the leverage or move the stop.")
    if margin > trade.equity:
        w.append("Required margin is larger than the account equity.")
    if qty == 0:
        w.append("Position rounds down to zero at this lot step: the risk budget is too small.")
    return result
