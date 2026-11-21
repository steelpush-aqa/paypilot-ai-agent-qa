import pytest

from app.engines import fx, policy

TIERS = list(policy.TIERS)
CURRENCIES = list(policy.RATES_TO_EUR)
CUR_A = CURRENCIES[0]
CUR_B = CURRENCIES[1] if len(CURRENCIES) > 1 else CURRENCIES[0]
TRANSFER_TYPES = list(policy.TRANSFER_FEES)


def _tier_with_finite_allowance():
    for t in TIERS:
        if policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[t] > 0:
            return t
    pytest.skip("немає тіру з ненульовим лімітом")


# ---------- mid_rate ----------

def test_mid_rate_same_currency_is_one():
    assert fx.mid_rate(CUR_A, CUR_A) == pytest.approx(1.0)


@pytest.mark.parametrize("a", CURRENCIES)
@pytest.mark.parametrize("b", CURRENCIES)
def test_mid_rate_is_ratio_of_eur_rates(a, b):
    expected = policy.RATES_TO_EUR[a] / policy.RATES_TO_EUR[b]
    assert fx.mid_rate(a, b) == pytest.approx(expected)


def test_mid_rate_inverse_pair_multiplies_to_one():
    assert fx.mid_rate(CUR_A, CUR_B) * fx.mid_rate(CUR_B, CUR_A) == pytest.approx(1.0)


def test_mid_rate_unknown_from_currency():
    with pytest.raises(ValueError, match="Unknown currency: XXX"):
        fx.mid_rate("XXX", CUR_A)


def test_mid_rate_unknown_to_currency():
    with pytest.raises(ValueError, match="Unknown currency: YYY"):
        fx.mid_rate(CUR_A, "YYY")


# ---------- quote: валідація ----------

def test_quote_unknown_tier():
    with pytest.raises(ValueError, match="Unknown tier: nope"):
        fx.quote(100, CUR_A, CUR_B, "nope")


def test_quote_unknown_currency():
    with pytest.raises(ValueError, match="Unknown currency"):
        fx.quote(100, "XXX", CUR_B, TIERS[0])


# ---------- quote: в межах ліміту ----------

def test_quote_within_allowance_has_no_spread():
    tier = _tier_with_finite_allowance()
    q = fx.quote(1.0, CUR_A, CUR_B, tier)
    if not q.allowance_applied:
        pytest.skip("1 одиниця перевищує ліміт для цього тіру")
    assert q.spread_pct == 0.0
    assert q.spread_amount == 0.0
    assert q.final_amount == pytest.approx(q.gross_amount)
    assert q.gross_amount == pytest.approx(1.0 * fx.mid_rate(CUR_A, CUR_B))


def test_quote_fields_echo_inputs():
    tier = TIERS[0]
    q = fx.quote(10.0, CUR_A, CUR_B, tier, allowance_used_eur=5.0)
    assert q.from_currency == CUR_A
    assert q.to_currency == CUR_B
    assert q.amount == 10.0
    assert q.tier == tier
    assert q.allowance_used_before_eur == 5.0
    assert q.allowance_total_eur == policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    assert q.mid_rate == pytest.approx(fx.mid_rate(CUR_A, CUR_B))


def test_quote_zero_amount():
    q = fx.quote(0.0, CUR_A, CUR_B, TIERS[0])
    assert q.gross_amount == 0.0
    assert q.spread_amount == 0.0
    assert q.final_amount == 0.0


def test_quote_allowance_boundary_is_inclusive():
    """used + amount == total -> ще в межах ліміту (<=)."""
    tier = _tier_with_finite_allowance()
    total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    amount = 100.0
    amount_eur = policy.to_eur(amount, CUR_A)
    used = total - amount_eur
    q = fx.quote(amount, CUR_A, CUR_B, tier, allowance_used_eur=used)
    assert q.allowance_applied is True
    assert q.spread_pct == 0.0


def test_quote_just_over_boundary_charges_spread():
    tier = _tier_with_finite_allowance()
    total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    amount = 100.0
    amount_eur = policy.to_eur(amount, CUR_A)
    used = total - amount_eur + 0.01
    q = fx.quote(amount, CUR_A, CUR_B, tier, allowance_used_eur=used)
    assert q.allowance_applied is False
    assert q.spread_pct == policy.FX_SPREAD_PCT[tier]


# ---------- quote: понад ліміт ----------

def _over_limit_quote(tier, **kw):
    total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    return fx.quote(100.0, CUR_A, CUR_B, tier, allowance_used_eur=total + 1.0, **kw)


@pytest.mark.parametrize("tier", TIERS)
def test_quote_over_limit_uses_tier_spread(tier):
    q = _over_limit_quote(tier)
    assert q.allowance_applied is False
    assert q.spread_pct == policy.FX_SPREAD_PCT[tier]
    assert q.spread_amount == pytest.approx(q.gross_amount * q.spread_pct / 100.0)
    assert q.final_amount == pytest.approx(q.gross_amount - q.spread_amount)


def test_quote_spread_override_applies_when_over_limit():
    q = _over_limit_quote(TIERS[0], spread_pct_override=2.5)
    assert q.spread_pct == 2.5
    assert q.spread_amount == pytest.approx(q.gross_amount * 0.025)


def test_quote_spread_override_zero_is_respected():
    """override=0.0 не повинен ігноруватись як falsy."""
    q = _over_limit_quote(TIERS[0], spread_pct_override=0.0)
    assert q.spread_pct == 0.0
    assert q.spread_amount == 0.0
    assert q.final_amount == pytest.approx(q.gross_amount)


def test_quote_spread_override_ignored_within_allowance():
    tier = _tier_with_finite_allowance()
    q = fx.quote(0.0, CUR_A, CUR_B, tier, spread_pct_override=5.0)
    if q.allowance_applied:
        assert q.spread_pct == 0.0


# ---------- quote: partial_allowance ----------

def test_partial_allowance_charges_only_excess_share():
    tier = _tier_with_finite_allowance()
    total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    amount = 1000.0
    amount_eur = policy.to_eur(amount, CUR_A)
    remaining = total / 2
    used = total - remaining
    if amount_eur <= remaining:
        pytest.skip("сума не перевищує залишок ліміту")
    q = fx.quote(amount, CUR_A, CUR_B, tier, allowance_used_eur=used,
                 partial_allowance=True)
    share = (amount_eur - remaining) / amount_eur
    expected = q.gross_amount * share * policy.FX_SPREAD_PCT[tier] / 100.0
    assert q.allowance_applied is False
    assert q.spread_amount == pytest.approx(expected)
    assert q.final_amount == pytest.approx(q.gross_amount - expected)


def test_partial_allowance_is_cheaper_than_full_spread():
    tier = _tier_with_finite_allowance()
    total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    amount = 1000.0
    used = total / 2
    full = fx.quote(amount, CUR_A, CUR_B, tier, allowance_used_eur=used)
    part = fx.quote(amount, CUR_A, CUR_B, tier, allowance_used_eur=used,
                    partial_allowance=True)
    if full.allowance_applied:
        pytest.skip("сума в межах ліміту")
    assert part.spread_amount <= full.spread_amount


def test_partial_allowance_fully_exhausted_equals_full_spread():
    tier = _tier_with_finite_allowance()
    total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    used = total + 50.0
    full = fx.quote(100.0, CUR_A, CUR_B, tier, allowance_used_eur=used)
    part = fx.quote(100.0, CUR_A, CUR_B, tier, allowance_used_eur=used,
                    partial_allowance=True)
    assert part.spread_amount == pytest.approx(full.spread_amount)


def test_partial_allowance_no_effect_within_limit():
    tier = _tier_with_finite_allowance()
    a = fx.quote(0.0, CUR_A, CUR_B, tier, partial_allowance=True)
    b = fx.quote(0.0, CUR_A, CUR_B, tier, partial_allowance=False)
    assert a == b


def test_partial_allowance_with_override():
    tier = _tier_with_finite_allowance()
    total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
    q = fx.quote(100.0, CUR_A, CUR_B, tier, allowance_used_eur=total + 10,
                 spread_pct_override=3.0, partial_allowance=True)
    assert q.spread_pct == 3.0
    assert q.spread_amount == pytest.approx(q.gross_amount * 0.03)


# ---------- FxQuote.as_dict ----------

def test_as_dict_contains_all_fields_and_rounds_floats():
    q = fx.FxQuote("A", "B", 1.0, 1.123456789, "t", 0.5, 10.0, 0.0, False,
                   1.123456789, 0.0123456789, 1.1111111111)
    d = q.as_dict()
    assert set(d) == {
        "from_currency", "to_currency", "amount", "mid_rate", "tier",
        "spread_pct", "allowance_total_eur", "allowance_used_before_eur",
        "allowance_applied", "gross_amount", "spread_amount", "final_amount"}
    assert d["mid_rate"] == 1.123457
    assert d["spread_amount"] == 0.012346
    assert d["final_amount"] == 1.111111
    assert d["allowance_applied"] is False
    assert d["from_currency"] == "A"


# ---------- transfer_fee ----------

@pytest.mark.parametrize("ttype", TRANSFER_TYPES)
def test_transfer_fee_formula(ttype):
    flat, pct = policy.TRANSFER_FEES[ttype]
    res = fx.transfer_fee(250.0, ttype)
    assert res["transfer_type"] == ttype
    assert res["amount_eur"] == 250.0
    assert res["flat_fee_eur"] == flat
    assert res["percent_fee"] == pct
    assert res["total_fee_eur"] == round(flat + 250.0 * pct / 100.0, 2)


@pytest.mark.parametrize("ttype", TRANSFER_TYPES)
def test_transfer_fee_zero_amount_is_flat_only(ttype):
    flat, _ = policy.TRANSFER_FEES[ttype]
    assert fx.transfer_fee(0.0, ttype)["total_fee_eur"] == round(flat, 2)


def test_transfer_fee_rounds_to_two_decimals():
    ttype = TRANSFER_TYPES[0]
    res = fx.transfer_fee(33.333333, ttype)
    assert res["total_fee_eur"] == round(res["total_fee_eur"], 2)


def test_transfer_fee_unknown_type():
    with pytest.raises(ValueError, match="Unknown transfer type: bogus"):
        fx.transfer_fee(100.0, "bogus")
