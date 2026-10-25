# PayPilot — QA of an LLM banking support agent

Testing and evaluation of an AI support agent for a fictional neobank. The agent uses tools for account queries, transfers, FX quotes and disputes, and retrieves information from internal documentation.

The project consists of three parts: building a golden dataset from customer complaints, investigating RAG failures, and testing how the agent handles memory across long conversations. 
Each part is based on observed failure evidence rather than the agent’s own answers.


## Contents

- [The system under test](#the-system-under-test)
- [How I work](#how-i-work)
- [1. Golden dataset from real complaints](#1-golden-dataset-from-real-complaints)
- [2. RAG failure localisation](#2-rag-failure-localisation)
- [3. Multi-turn memory](#3-multi-turn-memory)
- [Findings beyond the course](#findings-beyond-the-course)
- [Limitations](#limitations)

## The system under test

**PayPilot** is the support agent of **Verta**, a fictional neobank, run on a training stand
([paypilot-stand-shared](https://github.com/sergeytkachenko/paypilot-stand-shared), MIT licence).

```
customer ──► agent (Claude Haiku) ──► tools: accounts · transactions · limits · FX quotes · dispute eligibility · disputes
                     │
                     └──► retrieval over the bank's internal documentation (tariffs, limits, dispute rules)
```

- **Oracles.** The bank's rules are implemented in Python engines for FX pricing, transfer limits and dispute windows. They provide expected results independently of the agent's responses.
- **Defect profiles.** The stand supports profiles with specific defects enabled, such as a broken retrieval index, a lossy conversation summary or a prompt overlay. The `clean` profile serves as the baseline for comparison.
- **Traces.** Each turn records tool calls, arguments and results, retrieved document fragments, and the conversation summary. The analysis is based on this evidence, not just on the final response.

## How I work

| Principle | In practice |
|---|---|
| **Evidence from the step's inputs, not from the reply** | a failure is attributed only after reading what the model received: tool results, retrieved fragments, the summarised history |
| **Independent oracles** | expected values come from the engines, the documentation or a human rubric, and never from the agent's own earlier answer |
| **Five runs per claim** | LLM behaviour varies between runs, so results are reported as distributions ("4 of 5"), not single verdicts |
| **Prediction before the run** | predictions are committed before each run; mismatches are explained, not hidden |
| **Measured cost** | every suite run reports tokens and dollars, and the cost decides where a test runs (daily vs before a release) |
| **Testing the tests** | when a check fails on the healthy system, the check is investigated first |

## 1. Golden dataset from real complaints

*A golden dataset of 37 cases built from customer complaints and engine-derived edge cases, with an assertion
ladder from exact checks to a human rubric, and a CI gate.* This section is still in progress.

## 2. RAG failure localisation

*Investigating where RAG answers fail: indexing, retrieval or generation. The analysis uses retrieved fragments and controlled comparisons, including the effect of `top_k` on retrieval quality and cost. This section is still in progress.

## 3. Multi-turn memory

*Where a long conversation loses the case, why, and how to catch it automatically: a degradation profile,
5 dialogue cases with invariants, and a test plan priced in agent turns.* This section is still in progress.

## Findings beyond the course

The stand's defects are planted; these are things I found on top of them.

- **One compaction per session.** Reading the stand's code showed the history is compacted exactly once, so the
  turn at which the case is lost is fixed, not random.
- **A green check on a broken memory.** An amount check passed because a tool re-fetched the amount, while the
  agent no longer knew which of two identical charges was disputed.
- **A substituted value is worse than a missing one.** A missing amount was re-fetched; a shifted amount was used,
  and the customer was quoted a wrong fee.
- **False positives traced and fixed by test design.** A check failing on the healthy system was diagnosed as a
  wording problem and fixed, with a new prediction committed before the rerun.
- **An unconfirmed write.** The healthy agent filed a dispute without the explicit confirmation it had asked for.
- **The search query, not the user's language, decides retrieval.** Questions in English vs other languages produced the
  same English search query.
- **A cheap setting that isn't.** With a smaller `top_k`, the agent made an uninstructed second search, which cost
  60% more than the larger setting.

## Limitations

- A training stand with a fictional bank and planted defects: the methods transfer, the specific numbers don't.
- One model family (Claude Haiku 4.5 for projects 1–2, Haiku 5.5 for project 3); results may differ on others.
- Five runs per claim is enough to see a distribution, not to estimate a small failure rate precisely.
- Full reports, raw run data and commit history are in the original project repositories (in Ukrainian).


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
> therefore not runnable on its own — it documents what I added and how the expected values are derived.

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
