# Tool-call testing: verifying what the agent did, not what it said

*Checking an agent's actions through tool-call spans and the database row after a write, not its reply. One requirement becomes two checks at different prices: a deterministic one daily, a model-choice one before release.*

**Question.** An agent can reply "I've opened your dispute" while the tool wrote the dispute to the wrong account, in the wrong currency, or didn't write it at all. The reply looks correct. Where is the real evidence, and which checks are cheap enough to run every day versus only before a release?

**Setup.** The agent runs against defect profiles that each break the *action* while leaving the *reply* intact: a dispute written to a twin account (D12), a dispute written in the account's currency instead of the transaction's (D11), a retry loop on an empty tool result (D14), a tool description swapped to mislead tool choice (D13), and a garbled eligibility result (D29). A model mock replays earlier dialogue turns so one live step is tested on a stable history.

## What I built

- **Six scenarios of my own** ([`scenarios.jsonl`](scenarios.jsonl)): each checks the tool call, its arguments, the call order, the result contract, or the database row after the write — never the reply text. Every scenario carries its dimension, ladder level, gate and run count. The course kit's starter scenarios (S1, S2, S4, S5) are the academy's and are not included, so this file is not runnable on its own.
- **One requirement split by cost.** A deterministic verdict (state after a code defect, a result contract, a repeat) runs daily with one run. A model-choice verdict (tool choice, order, refusal, a parameter recalled from history) runs before release, five times, judged by majority.
- **A confirmation scenario of my own (R-F06).** An irreversible write (`create_dispute`) must not happen before explicit confirmation — checked both by the call count and by the empty database row.
- **Blocking-check costs measured from span durations**, so the policy names a real millisecond figure, not "fast".

## Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **A correct reply over a wrong write.** Under D12 the dispute is filed on the customer's twin account (ACC-1002/EUR instead of ACC-1003/USD). The call and its arguments are green; only the database row is wrong. The reply is correct word for word. | case S1, `state_row` check |
| 2 | **Same call, wrong currency.** Under D11 `create_dispute` writes the dispute in the account's currency (EUR) instead of the transaction's (USD) — 0/1 under the defect, 1/1 clean. A customer disputing a USD charge gets a EUR dispute: invisible in the reply and in the call arguments, visible only in the stored row. | case S-D11, deterministic |
| 3 | **The confirmation lives in the prompt, not the code.** My R-F06 scenario passed 5/5 when the agent had just said "reply yes to confirm" — but my earlier red-teaming work showed the same agent files early 3/5 without that prompt. Prompt-level confirmation works when it fires; it is not a code-level guarantee. | case R-F06 vs. SEC-906 (project 4) |
| 4 | **A garbled result turns into a forbidden write.** When the eligibility tool returns an unreadable result (D29), the agent opens a dispute that should have been refused — in 5 of 5 runs. The contract break is caught deterministically (daily, S3A); the behaviour it causes is probabilistic (release, five runs, S3B). | cases S3A / S3B |
| 5 | **A lying tool description steers tool choice.** Under D13 the limits tool's description is marked "deprecated" and the transactions tool "authoritative", so the agent answers an affordability question from transaction history instead of the limits tool — 5 of 5. Caught by a sequence check, not by the reply. | case S-D13 |

**One requirement, two prices.** Opening a dispute is irreversible, so the boundary matters. A payload check in code costs milliseconds (measured from the `create_dispute` span, ~3.9 ms) and runs daily; an engine re-check (`check_dispute_eligibility` before the write) costs an extra call (~0.9 ms on this stand, seconds on a real network); a human in the loop costs a queue. The policy names each form's cost and the legitimate scenario it would break.

**Method applied across projects.** The discipline is the same one used for retrieval and memory earlier: don't trust the surface, open the trace. Here the surface is the reply and the trace is the tool-call span plus the database row after the write.
