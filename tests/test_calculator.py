import unittest

from perprisk.calculator import (Trade, analyze, breakeven_price, liquidation_price,
                                 max_leverage_before_stop, pnl_at, position_size)

# Worked example used throughout (see docs/code-walkthrough.md):
# long 60,000 -> stop 58,800 (2 % away), equity 10,000, risk 1 % = $100, 10x, fee 0.055 %, MMR 0.5 %
LONG = dict(side="long", entry=60000, stop=58800, equity=10000, risk_pct=1, leverage=10)


class FormulaTests(unittest.TestCase):
    def test_liquidation_long_and_short(self):
        self.assertAlmostEqual(liquidation_price("long", 60000, 10, 0.005), 54300)
        self.assertAlmostEqual(liquidation_price("short", 60000, 10, 0.005), 65700)

    def test_breakeven_covers_both_fees(self):
        be = breakeven_price("long", 60000, 0.00055)
        self.assertAlmostEqual(pnl_at("long", 60000, be, 1, 0.00055), 0, places=9)
        be_short = breakeven_price("short", 60000, 0.00055)
        self.assertAlmostEqual(pnl_at("short", 60000, be_short, 1, 0.00055), 0, places=9)

    def test_max_leverage_before_stop(self):
        # 1 / (1 + 0.005 - 58800/60000) = 1 / 0.025 = 40x
        self.assertAlmostEqual(max_leverage_before_stop("long", 60000, 58800, 0.005), 40)
        # at exactly 40x the liquidation price equals the stop
        self.assertAlmostEqual(liquidation_price("long", 60000, 40, 0.005), 58800)

    def test_pnl_sign_for_short(self):
        self.assertGreater(pnl_at("short", 100, 90, 1, 0), 0)
        self.assertLess(pnl_at("short", 100, 110, 1, 0), 0)


class SizingTests(unittest.TestCase):
    def test_position_size_includes_fees(self):
        # loss per coin = 1,200 + 0.00055 x (60,000 + 58,800) = 1,265.34 -> 100 / 1,265.34 coins
        self.assertAlmostEqual(position_size(Trade(**LONG)), 100 / 1265.34)

    def test_loss_at_stop_equals_risk_budget(self):
        r = analyze(Trade(**LONG))
        self.assertAlmostEqual(r["loss_at_stop_usdt"], 100)
        self.assertAlmostEqual(r["loss_at_stop_pct_equity"], 1)

    def test_lot_step_rounds_down(self):
        qty = position_size(Trade(**LONG, lot_step=0.001))
        self.assertAlmostEqual(qty, 0.079)
        self.assertLessEqual(analyze(Trade(**LONG, lot_step=0.001))["loss_at_stop_usdt"], 100)


class AnalyzeTests(unittest.TestCase):
    def test_clean_trade_has_no_warnings(self):
        self.assertEqual(analyze(Trade(**LONG))["warnings"], [])

    def test_warns_when_liquidation_before_stop(self):
        r = analyze(Trade(**{**LONG, "leverage": 50}))
        self.assertTrue(any("liquidation comes BEFORE the stop" in w for w in r["warnings"]))

    def test_reward_to_risk(self):
        r = analyze(Trade(**LONG, take_profit=63600))
        # +3,600 per coin before fees vs -1,200: about 2.8:1 once fees are included
        self.assertGreater(r["reward_to_risk"], 2.7)
        self.assertLess(r["reward_to_risk"], 3.0)

    def test_funding_direction(self):
        long_cost = analyze(Trade(**LONG, funding_rate=0.0001, holding_hours=24))["funding_cost_est_usdt"]
        short = dict(LONG, side="short", stop=61200)
        short_cost = analyze(Trade(**short, funding_rate=0.0001, holding_hours=24))["funding_cost_est_usdt"]
        self.assertGreater(long_cost, 0)   # longs pay when funding is positive
        self.assertLess(short_cost, 0)     # shorts receive

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            Trade(**{**LONG, "stop": 61000})          # long stop above entry
        with self.assertRaises(ValueError):
            Trade(**{**LONG, "side": "sideways"})
        with self.assertRaises(ValueError):
            Trade(**{**LONG, "leverage": 0})


if __name__ == "__main__":
    unittest.main()
