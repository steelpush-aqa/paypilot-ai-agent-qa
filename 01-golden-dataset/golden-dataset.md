## 1. Golden dataset from customer complaints

The work started with 20 customer complaints. Each was assessed for whether it could be turned into a useful automated test, what the test should check, and where the expected result should come from.

### Dataset

- **12 complaints** were ready to automate, **5** needed more context, and **3** were not suitable for automation.
- **22 cases** were added to [\`golden.jsonl\`](golden.jsonl):
  - **10 complaint-based cases** covering dispute windows, FX quotes, promises the agent must not make, and five cases judged against a human rubric for tone and handling.
  - **12 FX boundary cases** covering conversions at and just above the free monthly allowance, across three customers on different tiers.
- Expected amounts and dispute windows were calculated using the bank's deterministic FX, limits and disputes engines. The additions are in [\`golden_extensions.py\`](golden_extensions.py).
- Each case records its assertion level, oracle, severity, and whether it belongs in the daily or pre-release suite.

> The course supplied the base generator and 15 starter cases. Only the additions are published here. \`golden_extensions.py\` is not a standalone script; it documents the changes and how expected values are derived.

### Findings that changed the test approach

| Finding | Why it matters | Evidence |
|---|---|---|
| **Going 1 EUR over the free allowance changes the cost by 8.71 USD.** At exactly 1,000 EUR there is no spread; at 1,001 EUR the spread applies to the whole amount. | A normal mid-range test would miss this boundary. The same pair catches a defect that charges the spread only on the amount above the allowance. | FX-006 / FX-007: 1,086.96 vs 1,078.25 USD |
| **The numeric helper can give the wrong result.** It merges "60, 90 and 120" into \`6090\` and \`120\`, reads "September 8, 2026" as \`82026\`, and drops "60" before a line break. | A result can be wrong because of the assertion helper, not the agent. | Reproduced with the helper and actual answers |
| **The agent can be right while the documentation is wrong.** A customer complained after being told 60 days for a duplicate-charge dispute because the help page said 120 days. | This was recorded as a documentation risk, not an answer failure: the agent followed the bank's rule. | Complaint C-12 |
| **The same case produced different answers.** In one run the agent asked for clarification; in another it gave the wrong window and said "typically 120 days". The trace showed that the customer ID had been passed as an account ID, returning an empty result, after which the agent answered from prior context. | The variation justified running unstable cases more than once. | Three runs of CMP-012 |

### Run results

| Setup | Daily suite result |
|---|---:|
| Clean system | 31/32 passed |
| Defect profile with five planted defects enabled | 14/32 passed |

At least one case caught each of the five planted defects.

One prediction did not hold up. A prompt change was expected to break a case, but it did not. A control run showed the same behaviour without the change, so the prediction was not reported as confirmed.

The 22 published cases are additions to the course material. The daily-suite results above cover the larger suite, including the course's starter cases.

### Run cost

One daily run used 68 model calls and 169k tokens, costing about $0.20 with Claude Haiku 4.5.
