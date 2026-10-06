"""Command line: python -m perprisk --side long --entry 60000 --stop 58800 --equity 10000 --risk-pct 1 --leverage 10"""

import argparse
import math
import sys

from .calculator import Trade, analyze

LABELS = [
    ("quantity", "Position size (coins)", "{:,.6f}"),
    ("notional_usdt", "Position value (USDT)", "{:,.2f}"),
    ("initial_margin_usdt", "Margin required (USDT)", "{:,.2f}"),
    ("liquidation_price_est", "Liquidation price (estimate)", "{:,.2f}"),
    ("max_leverage_before_stop", "Max leverage before stop", "{:,.1f}x"),
    ("loss_at_stop_usdt", "Loss if stop is hit (USDT)", "{:,.2f}"),
    ("loss_at_stop_pct_equity", "Loss if stop is hit (% equity)", "{:,.2f} %"),
    ("entry_plus_exit_fees_at_stop", "Fees included in that loss", "{:,.2f}"),
    ("breakeven_price", "Break-even price after fees", "{:,.2f}"),
    ("funding_cost_est_usdt", "Funding cost estimate (USDT)", "{:,.2f}"),
    ("profit_at_target_usdt", "Profit at take-profit (USDT)", "{:,.2f}"),
    ("reward_to_risk", "Reward : risk", "{:,.2f}"),
]


def main(argv=None):
    p = argparse.ArgumentParser(prog="perprisk", description="Position size, liquidation and fee check "
                                "for a USDT perpetual futures trade. Educational; not investment advice.")
    p.add_argument("--side", choices=["long", "short"], required=True)
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--equity", type=float, required=True, help="account equity in USDT")
    p.add_argument("--risk-pct", type=float, required=True, help="%% of equity to risk, e.g. 1")
    p.add_argument("--leverage", type=float, required=True)
    p.add_argument("--take-profit", type=float)
    p.add_argument("--fee-rate", type=float, default=0.00055, help="per side, default 0.00055 (0.055%%)")
    p.add_argument("--mmr", type=float, default=0.005, help="maintenance margin rate, default 0.005")
    p.add_argument("--lot-step", type=float, default=0.0, help="quantity increment, e.g. 0.001")
    p.add_argument("--funding-rate", type=float, default=0.0, help="per 8 h, e.g. 0.0001")
    p.add_argument("--hours", type=float, default=0.0, help="expected holding time in hours")
    a = p.parse_args(argv)

    try:
        trade = Trade(a.side, a.entry, a.stop, a.equity, a.risk_pct, a.leverage, a.fee_rate, a.mmr,
                      a.lot_step, a.take_profit, a.funding_rate, a.hours)
    except ValueError as err:
        sys.exit(f"error: {err}")

    result = analyze(trade)
    for key, label, fmt in LABELS:
        value = result.get(key)
        if value is None:
            continue
        text = "no limit" if value == math.inf else fmt.format(value)
        print(f"{label:<32} {text}")
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()
