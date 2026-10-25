# PayPilot: QA of an LLM banking support agent

This project looks at how to test an AI support agent for a fictional neobank. The agent can look up accounts, make transfers, get FX quotes and handle disputes. It also retrieves information from the bank's internal documentation.

I split the work into three parts: building a golden dataset from complaint scenarios, finding where RAG answers fail, and checking what the agent remembers across long conversations. I use traces and independent expected results, not the agent's own answers, to investigate failures.

## Contents

- [The system under test](#the-system-under-test)
- [How I approach testing](#how-i-approach-testing)
- [1. Golden dataset](#1-golden-dataset)
- [2. RAG diagnostics](#2-rag-diagnostics)
- [3. Multi-turn memory](#3-multi-turn-memory)
- [Findings](#findings)
- [Limitations](#limitations)

## The system under test

**PayPilot** is a support agent for **Verta**, a fictional neobank. It runs on the training stand [paypilot-stand-shared](https://github.com/sergeytkachenko/paypilot-stand-shared), which is MIT-licensed.

```
customer --> agent (Claude Haiku) --> tools: accounts, transactions, limits, FX quotes, dispute eligibility, disputes
                    |
                    +--> retrieval over internal documentation (tariffs, limits, dispute rules)
```

- **Independent expected results.** The bank's rules are implemented in Python engines for FX pricing, transfer limits and dispute windows. I use those engines to get expected values independently of the agent.
- **Defect profiles.** The stand can enable specific defects, such as a broken retrieval index, a conversation summary that loses details, or a prompt overlay. I compare these runs with the `clean` profile.
- **Traces.** Each turn records tool calls, their arguments and results, retrieved fragments, and the conversation summary. I use this evidence to work out where a failure started.

## How I approach testing

| Principle | How I apply it |
|---|---|
| Check the inputs, not only the reply | Before blaming generation, I check the tool results, retrieved fragments and conversation summary the model actually received. |
| Use an independent source of truth | Expected values come from the bank's engines, documentation or a human rubric, not from an earlier answer by the agent. |
| Repeat variable cases | LLM responses can change between runs, so I report results such as "4 of 5" rather than relying on one run. |
| Record predictions first | I write down what I expect before running a case, then explain any mismatch. |
| Measure the cost | I record tokens and cost for each suite run and use that information to decide which checks belong in the daily suite and which should run before a release. |
| Check the checks | When a test fails on the clean system, I investigate the assertion before assuming the agent is broken. |

## 1. Golden dataset

I sorted 20 complaint scenarios by whether they were ready for automation, needed more context, or were not suitable. I then added 22 test cases with expected values derived from the bank's deterministic engines or human rubrics.

The boundary cases caught an important FX rule: going 1 EUR over the free allowance applies the spread to the whole conversion, not just the extra euro.

**[Read the report](01-golden-dataset/golden-dataset.md)** · [Test cases](01-golden-dataset/golden.jsonl) · [Generator changes](01-golden-dataset/golden_extensions.py)

The 22 cases published here are my additions. The daily-suite results in the report cover a larger suite, including the course's starter cases. The base generator and starter cases are not included in this repository, so the published extension is not runnable on its own.

## 2. RAG diagnostics

I investigated whether retrieval failures came from the index, the search results or the model's use of the retrieved text. The report includes six failure investigations, a controlled index comparison, a cost comparison for `top_k` settings, and 11 retrieval cases with expected text taken from the documentation.

**[Read the report](02-rag-diagnostics/rag-diagnostics.md)** · [Retrieval cases](02-rag-diagnostics/retrieval-cases.jsonl)

## 3. Multi-turn memory

I followed the conversation summary turn by turn to find when the agent lost details needed for a dispute. The report covers five dialogue cases, checks for missing and substituted values, and an action that was recorded without the confirmation the agent had requested.

**[Read the report](03-multi-turn-memory/multi-turn-memory.md)** · [Dialogue cases](03-multi-turn-memory/l05_dialogs.jsonl)

## Findings

These are the main issues I found while working through the cases. The stand also has planted defects, so I distinguish those from issues in my own evaluation setup.

**Golden dataset**
- **An FX boundary case worth 8.71 USD.** The spread changes when a conversion goes just over the free allowance.
- **A problem in the numeric helper.** It can merge, misread or drop numbers, which means the assertion itself can give the wrong result.
- **A documentation mismatch.** The agent followed the bank's dispute rule, but the help page gave a different window.

**RAG diagnostics**
- **The user's language did not change the search query.** Questions in Ukrainian and English produced the same English query and the same retrieved fragments.
- **I reproduced the broken index.** Rebuilding its text slicing offline matched the fragments in the traces and showed which table rows had been split.
- **Some information came from the tool schema.** The agent listed dispute reason codes in the schema's order, not the order in the documentation.

**Multi-turn memory**
- **The amount check passed while the case details were lost.** The agent fetched the amount again but no longer knew which of two identical charges was being disputed.
- **A substituted amount led to a wrong fee.** The agent used the changed value before correcting itself later.
- **A dispute was filed without confirmation.** The clean agent took the action even though the customer had not given the explicit confirmation it had asked for.

## Limitations

- This is a training stand with a fictional bank and planted defects. The testing methods may transfer to other systems, but the specific figures and failures are from this stand.
- I used Claude Haiku 4.5 for projects 1 and 2, and Haiku 5.5 for project 3. Results may differ with other models.
- Five runs per case help show variation, but are not enough to estimate a low failure rate precisely.
- The full reports, run data and commit history are available in the original course project repositories, which are in Ukrainian.
