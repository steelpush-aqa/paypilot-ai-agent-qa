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

A test set built from customer complaints and from the bank's own rules rather than from the agent's answers:
complaint triage, 22 cases with expected values derived from deterministic engines, and an assertion level and
oracle documented for each case. Boundary cases exposed an all-or-nothing allowance rule worth 8.71 USD to the
customer.
**→ [Full write-up](01-golden-dataset/golden-dataset.md)** · [cases](01-golden-dataset/golden.jsonl) ·
[generator extensions](01-golden-dataset/golden_extensions.py)

## 2. RAG failure localisation

Locating where a retrieval-augmented answer breaks: indexing, retrieval or generation — from the fragments the
model actually received, with a one-variable proof of cause, a priced `top_k` trade-off, and 11 retrieval cases
with expected answers taken verbatim from the documentation.
**→ [Full write-up](02-rag-diagnostics/rag-diagnostics.md)** · [retrieval cases](02-rag-diagnostics/retrieval-cases.jsonl)

## 3. Multi-turn memory

Where a long conversation loses the case, why, and how to catch it automatically: a turn-by-turn degradation
profile read from the compacted history, 5 dialogue cases with invariants and "forbid" rules, and a test plan
priced in agent turns. The case was lost at turn 3 in every run, but became visible only at turn 5.
**→ [Full write-up](03-multi-turn-memory/multi-turn-memory.md)** · [dialogue cases](03-multi-turn-memory/l05_dialogs.jsonl)

## Findings beyond the course

The stand's defects are planted; these are things I found on top of them.

**Golden dataset** ([write-up](01-golden-dataset/golden-dataset.md))
- **An all-or-nothing rule worth 8.71 USD.** Boundary cases showed that converting 1 EUR above the free allowance
  puts the spread on the whole amount — and isolated a defect no mid-range case caught.
- **A flaw in the evaluation tool.** The number-extraction helper behind numeric checks merges and drops numbers,
  so a check can pass or fail for reasons unrelated to the answer.

**RAG failure localisation** ([write-up](02-rag-diagnostics/rag-diagnostics.md))
- **The search query, not the user's language, decides retrieval.** Questions in Ukrainian and English produced
  the same English query, so an expected retrieval loss never happened.
- **Failures predicted from the index itself.** An offline rebuild of the broken index matched the trace
  fragments character for character, which told me before any run which table rows were split.
- **Facts from an unmeasured source.** A list in the agent's answer came from the tool schema, not the
  documentation, a channel retrieval metrics can't see.

**Multi-turn memory** ([write-up](03-multi-turn-memory/multi-turn-memory.md))
- **A green check on a broken memory.** A tool re-fetched the amount while the agent no longer knew which of two
  identical charges was disputed.
- **A substituted value is worse than a missing one.** A missing amount was re-fetched; a shifted one was used,
  and the customer was quoted a wrong fee.
- **An unconfirmed write.** The healthy agent filed a dispute without the explicit confirmation it had asked for.

## Limitations

- A training stand with a fictional bank and planted defects: the methods transfer, the specific numbers don't.
- One model family (Claude Haiku 4.5 for projects 1–2, Haiku 5.5 for project 3); results may differ on others.
- Five runs per claim is enough to see a distribution, not to estimate a small failure rate precisely.
- Full reports, raw run data and commit history are in the original project repositories (in Ukrainian).
