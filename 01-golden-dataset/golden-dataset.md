## 1. Golden dataset from real complaints

*A test set a CI gate can trust: built from customer complaints and from the bank's own rules, not from the
agent's answers.*

**Question.** Which customer complaints can become automated tests, what should each test check, and who decides
what the correct answer is?

### What I built

- **Complaint triage.** 20 customer complaints sorted into *ready to automate* (12), *needs context first* (5)
  and *not suitable for automation* (3), each with the reason.
- **22 test cases** ([`golden.jsonl`](01-golden-dataset/golden.jsonl)):
  - **10 from complaints** — dispute windows, FX quotes, a promise the agent must not make ("we will refund
    you"), and 5 cases scored against a human rubric (tone and handling, where no exact answer exists);
  - **12 FX edge cases** — conversions at and just above the customer's free monthly allowance, for three
    customers in different tiers, each paired with a check on the spread the agent states.
- **Expected values from the bank's engines**, not written by hand: the generator computes each expected amount
  and window from the deterministic FX, limits and disputes engines
  ([`golden_extensions.py`](01-golden-dataset/golden_extensions.py)).
- **Each case documents why it is checked the way it is**: an assertion level from exact equality to a human
  rubric (levels 1, 2, 3, 4 and 7 used), the oracle (engine or human), severity, and whether it runs daily or
  before a release.

> The dataset was generated with a course-provided generator, which I extended. Only my additions are published
> here: the base script and the course's 15 starter cases belong to the course. `golden_extensions.py` is
> therefore not runnable on its own, it documents what I added and how the expected values are derived.

### Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **Converting 1 EUR more costs the customer 8.71 USD.** The free allowance is all-or-nothing: at exactly 1,000 EUR no spread is charged; at 1,001 EUR the spread applies to the *whole* amount. Only the boundary pair shows this — a mid-range case hides it. The same pairs isolate a defect that applies the spread only to the excess, which no other case caught. | cases FX-006 / FX-007: 1,086.96 vs 1,078.25 USD |
| 2 | **A flaw in the numeric check itself.** The helper that extracts numbers from an answer merges "60, 90 and 120" into `6090` and `120`, reads "September 8, 2026" as `82026`, and drops "60" before a line break. A number-based check can pass or fail for reasons unrelated to the answer. | the extraction helper, reproduced on real answers |
| 3 | **A complaint whose cause is outside the agent.** A customer was told 60 days for a duplicate-charge dispute and complained, because the help page said 120. The agent was right: the documentation was wrong. Logged as a residual risk instead of a failing test. | complaint C-12: corpus vs help page |
| 4 | **The same case, three behaviours.** One dispute case asked for clarification in one run and stated a wrong window ("typically 120 days") in another. The cause: the agent passed the customer ID as an account ID, got an empty list and answered from its prior. That variance is why the unstable cases are marked for 5 runs. | three runs of case CMP-012 |

**Results.** The healthy system passed 31 of 32 daily cases; a defect profile with five planted defects dropped it
to 14 of 32, and every planted defect was caught by at least one case. One prediction missed and is recorded as
such: a prompt change I expected to break a case didn't, and a control run showed the same behaviour without it.

**Cost.** One daily run: 68 model calls, 169k tokens, about $0.20 (Claude Haiku 4.5).
