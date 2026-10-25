## 1. Golden dataset from customer complaints

I wanted to find out which customer complaints could become useful automated tests, what each test should check, and where the expected result should come from.

The main rule for this work was simple: I did not use the agent's answer as the source of truth.

### What I built

- **Complaint triage.** I sorted 20 complaints into three groups: ready to automate (12), needs more context (5), and not suitable for automation (3). Each decision has a reason.
- **22 test cases** ([`golden.jsonl`](golden.jsonl)):
  - **10 complaint-based cases** covering dispute windows, FX quotes, promises the agent must not make (such as "we will refund you"), and five cases checked against a human rubric for tone and handling.
  - **12 FX boundary cases** covering conversions at and just above the free monthly allowance. They cover three customers on different tiers and include a separate check for the spread stated by the agent.
- **Expected values from the bank's engines.** The generator calculates amounts and dispute windows using the deterministic FX, limits and disputes engines. My additions are in [`golden_extensions.py`](golden_extensions.py).
- **A reason for each assertion.** Each case records the assertion level, oracle, severity and whether it belongs in the daily suite or the pre-release suite. The checks range from exact values to a human rubric.

> The course supplied the base generator and 15 starter cases. I extended that generator, but only my additions are published here. `golden_extensions.py` is not a standalone script; it shows the changes I made and how expected values are derived.

### Findings

| # | What I found | Evidence |
|---|---|---|
| 1 | **Converting 1 EUR more changes the cost by 8.71 USD.** The free allowance is all-or-nothing. At exactly 1,000 EUR there is no spread; at 1,001 EUR the spread applies to the whole amount. A mid-range test would not catch this boundary. The same pair also catches a defect that charges the spread only on the amount above the allowance. | FX-006 / FX-007: 1,086.96 vs 1,078.25 USD |
| 2 | **The numeric check can give the wrong result.** The helper merges "60, 90 and 120" into `6090` and `120`, reads "September 8, 2026" as `82026`, and drops "60" before a line break. That means a test can pass or fail because of the helper, not because the answer is correct. | Reproduced with the number-extraction helper and actual answers |
| 3 | **The agent can be right while the documentation is wrong.** A customer was told 60 days for a duplicate-charge dispute and complained because the help page said 120 days. The agent followed the bank's rule. I recorded this as a documentation risk rather than marking the answer as a failure. | Complaint C-12: dispute rule vs help page |
| 4 | **The same case produced different answers.** In one run, the agent asked for clarification. In another, it gave the wrong window and said "typically 120 days". The trace showed that it passed the customer ID as an account ID, got an empty result and answered from its previous context. This is why unstable cases get five runs. | Three runs of CMP-012 |

### Results

The clean system passed 31 of 32 cases in the daily suite. With a defect profile that enabled five planted defects, the result dropped to 14 of 32. At least one case caught each planted defect.

I also recorded a prediction that did not hold up. I expected a prompt change to break a case, but it did not. A control run showed the same behaviour without the change, so I kept that result instead of presenting the prediction as confirmed.

The 22 cases published here are my additions. The daily-suite results cover the larger suite, including the course's starter cases.

### Cost

One daily run used 68 model calls and 169k tokens, costing about $0.20 with Claude Haiku 4.5.
