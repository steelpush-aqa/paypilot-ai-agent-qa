# Multi-turn memory

The goal was to identify when important details are lost in a long support conversation, why this happens, and how the problem can be caught by a test.

### Scenario

A customer reports that goods from a 240.00 EUR card payment never arrived. A few unrelated questions about the card limit and FX spread follow before the conversation returns to the dispute.

The stand summarises the conversation after two turns. In the defect profile, the summary can drop numbers (D06) or replace them with other values (D07).

### What was built

- **A turn-by-turn record of what the model received.** The compacted summary from the `agent.summarize` span and the retrieval context were checked over five runs per scenario.
- **Five dialogue cases** ([`l05_dialogs.jsonl`](l05_dialogs.jsonl)). They cover conversation length, the number of case details, and topic changes: a main scenario, a worst case, two cases isolating one variable at a time, and a control.
- **Checks for the right value and the wrong value.** At a later turn, the test checks the expected value and also forbids a likely substitution, such as the second identical charge or a different reason code. Expected values come from the bank's engine, not the agent's earlier answer. Repeating the same mistake therefore does not make the test pass.
- **Predictions recorded before each run.** The results were compared with those predictions afterwards.

> The `plan_role` values in the cases are in Ukrainian because the course loader accepts only those labels: `основний` means main, `найгірший` means worst case, `контроль` means control, and `ізоляція осі` means axis isolation.

### Findings

| # | What was found | Evidence |
|---|---|---|
| 1 | **The loss happened at the same turn every time.** The compaction code showed that the summary is created once per session, at turn threshold + 1. The case details were missing from the model's input at turn 3 in all five runs, but the customer-facing problem appeared at turn 5. The two replies in between looked normal. | Summary text from each run and the stand's `summarize.py` |
| 2 | **A tool call can hide memory loss.** After the details disappeared from the summary, the agent called `get_transactions` and recovered the amount. The amount check passed, but the agent no longer knew which of two identical 240.00 EUR charges was being disputed. In all five runs, a check on the amount alone missed the problem. | Case H04 |
| 3 | **A wrong value can be worse than a missing one.** When the summary dropped the amount, the agent fetched it again. When the defect changed it from 62.30 to 46.72, the agent used the wrong figure and quoted the customer the wrong fee. It corrected itself one turn later in two of five runs. | Control case H05: summary compared with reply |
| 4 | **The checks needed adjustment too.** A literal reason-code check failed in four of five runs on the clean system because the agent wrote the code in words. The check was changed to allow for wording differences, a turn that could legitimately invite a mention of the second charge was removed, and a new prediction was written before rerunning. The main scenario then passed four of five clean runs and zero of five runs with the defect enabled. | Version 1 and version 2 run reports |
| 5 | **An action risk was found that text checks would miss.** On the clean system, the agent filed a dispute without the explicit confirmation it had asked for. This was observed three times. Checking the response text is not enough here; the test needs to inspect the recorded action in the disputes table. | Trace from the filing turn |

### Cost

The dialogue suite uses 180 agent turns per profile and costs about $0.17 to $0.19 per run, roughly four times the single-turn suite. It is best suited to pre-release checks and runs whenever the conversation-compaction code changes, rather than on every commit.
