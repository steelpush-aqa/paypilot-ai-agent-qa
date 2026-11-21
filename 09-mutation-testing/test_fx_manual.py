import pytest

from app.engines import fx

def test_tier2_under_limit_no_spread():
    # tier2 free limit is EUR 1000; 500 EUR is within it -> no spread applied
    q = fx.quote(500, "EUR", "USD", "tier2")
    assert q.allowance_applied is True
    assert q.spread_pct == 0.0
    assert q.final_amount == pytest.approx(500 / 0.92)


def test_tier2_over_limit_charges_0_9_percent():
    # 1200 EUR is over the 1000 limit -> 0.9% spread on the whole amount
    q = fx.quote(1200, "EUR", "USD", "tier2")
    assert q.allowance_applied is False
    assert q.spread_pct == 0.9
    assert q.final_amount == pytest.approx(1200 / 0.92 * (1 - 0.9 / 100))


def test_tier2_exactly_on_limit_no_spread():
    # exactly at EUR 1000 the allowance still applies (<=), so no spread
    q = fx.quote(1000, "EUR", "USD", "tier2")
    assert q.allowance_applied is True
    assert q.spread_pct == 0.0


def test_tier1_over_limit_charges_1_5_percent():
    # tier1 limit is EUR 500, spread 1.5%; 600 EUR is over it
    q = fx.quote(600, "EUR", "USD", "tier1")
    assert q.allowance_applied is False
    assert q.spread_pct == 1.5


def test_tier2_allowance_already_used_pushes_over_limit():
    # 600 EUR alone is within, but 500 already used -> 1100 > 1000 -> spread applies
    q = fx.quote(600, "EUR", "USD", "tier2", allowance_used_eur=500)
    assert q.allowance_applied is False
    assert q.spread_pct == 0.9


def test_limit_is_checked_in_eur_not_raw_amount():
    # 1050 USD = 966 EUR, under the tier2 limit -> no spread,
    # even though the raw number 1050 is above 1000
    q = fx.quote(1050, "USD", "EUR", "tier2")
    assert q.allowance_applied is True
    assert q.spread_pct == 0.0
