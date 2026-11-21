"""Rewritten tests salvaged from rejected generated tests (L11, step 5).

R-01 rewrites G-13 (test_quote_over_limit_uses_tier_spread): the expected
spreads are written in from the tariff table, not read from policy at runtime,
so this version catches a bug IN the table (mutant A-01/A-02).
"""
import pytest

from app.engines import fx


@pytest.mark.parametrize("tier, limit, spread", [
    ("tier1", 500, 1.5),
    ("tier2", 1000, 0.9),
    ("tier3", 5000, 0.5),
])
def test_over_limit_uses_hardcoded_tier_spread(tier, limit, spread):
    # one unit over the tier limit, from EUR so amount == amount_eur
    q = fx.quote(limit + 1, "EUR", "USD", tier)
    assert q.allowance_applied is False
    assert q.spread_pct == spread
    assert q.final_amount == pytest.approx((limit + 1) / 0.92 * (1 - spread / 100))