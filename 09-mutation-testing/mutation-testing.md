# Mutation testing: judging a test set by what it kills

*Measuring whether an AI-generated test suite is trustworthy by running it against a fixed set of planted bugs, not by its coverage.*

**Question.** Line coverage tells you which lines ran, not whether a test would notice if a line were wrong. So when an assistant writes a whole test suite in seconds, how do you know it actually catches bugs? The honest way to find out is to plant a fixed set of small bugs and count how many each suite kills.

**Setup.** One module under test: the bank's FX pricing engine (`app/engines/fx.py`), which applies a per-tier spread once a conversion crosses the EUR 1000 free allowance. A frozen list of 12 mutants in four classes, committed before any test runs. Two suites are measured on that one ruler: a manual set I designed (6 tests, expected values written in from the tariff table) and an AI-generated set (26 functions, 69 cases) from a deliberately weak one-line prompt with no intervention. Six written acceptance criteria decide which generated tests to keep.

## What I built

- A frozen mutant list as the ruler. Twelve one-line bugs, three per class, committed before the first run so the score cannot be tuned to the tests.
- A manual baseline with an independent oracle. Expected spreads written in from the tariff table, not read back from the code under test.
- Six acceptance criteria, written before generation: oracle, assertion level, edge case, independence, name, novelty.
- A generation review log. Every one of the 26 generated tests accepted or rejected against those criteria, with the reason recorded. 14 rejected, 1 rewritten.

## The ruler: 12 mutants

| ID | Class | Change |
|---|---|---|
| A-01 | tier value | tier2 spread 0.9 → 1.5 |
| A-02 | tier value | tier1 spread 1.5 → 0.9 |
| A-03 | tier value | tier2 allowance 1000 → 500 |
| B-01 | EUR 1000 boundary | `<=` → `<` on the limit |
| B-02 | EUR 1000 boundary | drop used-allowance from the check |
| B-03 | EUR 1000 boundary | compare raw amount, not EUR |
| C-01 | arithmetic | `gross - spread` → `gross + spread` |
| C-02 | arithmetic | `/ 100` → `/ 10` (10x spread) |
| C-03 | arithmetic | `amount * rate` → `amount / rate` |
| D-01 | result shape | `allowance_applied` always True |
| D-02 | result shape | `as_dict` returns strings |
| D-03 | result shape | `as_dict` stops rounding floats |

## The result: kills by class

| Class | Manual | Generated | Combined |
|---|---|---|---|
| Tier value | 3/3 | 0/3 | 3/3 |
| EUR 1000 boundary | 3/3 | 2/3 | 3/3 |
| Arithmetic | 3/3 | 3/3 | 3/3 |
| Result shape | 1/3 | 3/3 | 3/3 |
| **Total** | **10/12 (83%)** | **8/12 (67%)** | **12/12 (100%)** |
| Line coverage | 64% | 100% | — |

Survivors: the manual set misses D-02 and D-03 (it checks values, not the types `as_dict` returns). The generated set misses A-01, A-02, A-03 and B-03 (it reads the spread and the limit from the tariff table at runtime, so a wrong table still passes).

## Findings

| # | Finding |
|---|---|
| 1 | **Coverage is not catching-ability.** The generated suite reached 100% line coverage but killed 8 of 12 mutants; the manual suite had 64% coverage and killed 10. More tests and more coverage did not make a better set. |
| 2 | **The oracle-from-the-system trap.** 8 of the 14 rejected generated tests take their expected value from the same tariff table the code reads, so they stay green even when that table is wrong, and cannot kill any tier-value mutant. |
| 3 | **Strong on shape, blind on values.** The assistant killed 3 of 3 result-shape mutants (the types and rounding of `as_dict`, which a human rarely doubts) and 0 of 3 tier-value mutants. The manual set was the exact mirror: 3 of 3 tier value, 1 of 3 shape. |
| 4 | **The union beats either alone.** Manual 10/12, generated 8/12, combined 12/12. The two suites are strong in different classes, so the assistant's value is specific classes of check, not replacing the person. |
| 5 | **The recommendation survives the mandate.** Under "ship it," keep the generated shape and error-path tests after review. Under "zero regulatory risk," every spread and limit test must be human with a number from the requirements, and a generated test whose oracle comes from the code is not accepted at all. |

## The oracle trap, concretely

The most common reason to reject a generated test (8 of 14) was that it read its expected value from the code it was testing. The rejected test G-13 and its hand-rewrite R-01 show it:

```python
# G-13, rejected: the "expected" spread is read from the same table fx.quote reads
assert q.spread_pct == policy.FX_SPREAD_PCT[tier]   # stays green even if that table is wrong

# R-01, rewritten: the spread is a fact written in from the tariff document
@pytest.mark.parametrize("tier, limit, spread", [
    ("tier1", 500, 1.5), ("tier2", 1000, 0.9), ("tier3", 5000, 0.5)])
def test_over_limit_uses_hardcoded_tier_spread(tier, limit, spread):
    q = fx.quote(limit + 1, "EUR", "USD", tier)
    assert q.spread_pct == spread                   # now a wrong table fails the test
```

G-13 cannot kill the tier-value mutants A-01 and A-02; R-01 can.

**The headline a CTO signs:** the generated suite had 100% coverage and still missed a quarter of the bugs the manual suite caught, because its tests read the answer from the code they were testing. The assistant earns its place on breadth and result shape. The oracle for the core pricing logic stays with a person.
