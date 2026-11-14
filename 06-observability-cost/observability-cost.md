# Observability and cost: proving what an agent really costs

*The number a system reports about itself can lie. Three independent price sources cross-check each other, the trace is the referee, and silent cost leaks become red tests through a per-dialogue budget.*

**Question.** An agent can answer correctly, pass every check, and still cost several times what its own cost field reports. Where is the real figure, what makes a dialogue quietly more expensive, and how do you turn a cost leak into something a test can fail on?

**Setup.** The agent runs against defect profiles that each raise cost while leaving the answer correct: a retry loop that re-calls the model on an empty tool result (D14), a context replay that re-reads all prior tool results every step (D15), and a history compression that loses the customer's case and forces a re-fetch. Every step is traced; cost is read from three places at once: the system's self-report (`usage.cost_usd`), the sum of the model-call spans priced by hand, and the provider's own bill (`usage.provider_cost_usd`).

## What I built

- **A three-source price check.** On a healthy step all three agree. When two agree and one lags, the odd one out is the liar, and the trace proves which.
- **Six budget cases** ([`budget_cases.jsonl`](budget_cases.jsonl)): each carries a `tokens_total`, `latency_ms` and `identical_tool_calls_max` ceiling. A dialogue over budget fails even when every answer is correct. Deterministic ceilings run daily; the token/latency ceilings run before release, judged by the median of five runs.
- **A threshold calibrated, not guessed.** For the main case the `tokens_total` ceiling is the clean baseline median plus a margin above the clean maximum, so normal model variance does not false-fail while the defect profile does.
- **A model-migration comparison** (Haiku vs. Gemini) by dialogue cost and checks, not list price.

## Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **The counter lies.** A hidden retry loop (the orchestration mistakes an empty tool result for a failure) re-calls the model up to eight times. `usage.cost_usd` undercounts the step ~5x; the span-sum and the provider bill agree on the real figure. Caught by counting identical tool calls. | D14, three-source check |
| 2 | **Tests green, bill grows.** Context replay re-reads all prior tool results every step. Every answer is correct, latency is unchanged, all three prices agree, and the dialogue costs ~29% more. No correctness check sees it; only a token budget does. | D15, 5-run median |
| 3 | **Saving that costs more.** Compressing history to save tokens loses the transaction number and dispute code, so the agent re-fetches, costing more than not compressing. The summary's own tokens show only in the provider bill, not the span-sum. | compression profile |
| 4 | **List price is not dialogue cost.** Haiku is 3-5x cheaper per token than Gemini but only ~30% cheaper per dialogue (different tokenizer, longer answers). The D15 token threshold tuned to Haiku goes blind on Gemini, passing a broken profile. One Gemini run cost 120x the baseline, hidden by the median, visible only in min-max. | migration table, 5 runs each |
| 5 | **A budget turns a silent leak into a test.** With a `tokens_total` ceiling calibrated from the clean median plus a margin, the dialogue passes on the clean profile and fails on the replay profile, the first check that makes D15 red. | C07-BUDGET, clean vs. defect |

**Measure the bottom, calculate the top.** The cost model has four floors: the step and the dialogue are measured from traces; the month and the N-user forecast are calculated from assumptions written down separately with their source. The forecast carries one line for what grows faster than the number of users, the replay excess grows with dialogue length, so a linear "800 to N" extrapolation misses it.

**Method applied across projects.** The same discipline as the earlier tool-call and memory work: don't trust the surface, open the trace. Here the surface is a cost field and the word "savings", and the trace plus the provider bill are the evidence.
