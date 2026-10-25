# Multi-turn memory

*Where a long conversation loses the case, why, and how to catch it automatically.*

**Question.** In a 7-turn dispute conversation every individual reply can pass a single-turn check, yet the
customer still ends up with the wrong dispute. At which turn does the agent lose the case, and how do you catch
it automatically?

**Setup.** A customer reports that the goods for a 240.00 EUR card payment never arrived, asks a few unrelated
questions (card limit, FX spread), then returns to the dispute. The stand compacts the conversation history into a
summary after 2 turns. The defect profile makes that summary drop numbers (D06) and substitute values (D07).

## What I built

- **Degradation profile** — for every turn, what the model actually received: the compacted summary text
  (`agent.summarize` span) and the retrieval context, over 5 runs per scenario.
- **5 dialogue cases** ([`l05_dialogs.jsonl`](l05_dialogs.jsonl)) chosen on three axes (length, number of case
  entities, topic switches): a main scenario, a worst case, two one-axis isolation pairs and a control.
- **Invariants with "forbid" rules** — the expected value at a later turn, plus the wrong value that must *not*
  appear (the second, identical charge; a substituted reason code). Expected values come from the bank's engine,
  not from the agent's own earlier reply, so a consistently wrong answer still fails.
- **Predictions committed before every run**, compared with the results afterwards.

> The `plan_role` values in the cases are in Ukrainian (`основний` main, `найгірший` worst case, `контроль`
> control, `ізоляція осі` axis isolation) because the course's loader accepts only those labels.

## Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **The loss turn is fixed, not random.** Reading the compaction code showed exactly one compaction per session, at turn *threshold + 1*. The case details left the model's input at turn 3 in 5 of 5 runs; the customer could see it only at turn 5. Two turns in between looked perfectly normal. | summary text per run; the stand's `summarize.py` |
| 2 | **Tools hide memory loss.** After the loss the agent re-fetched the amount with `get_transactions`, so an amount check stayed green — while it no longer knew *which* of two identical 240.00 EUR charges was the disputed one. A check on the wrong entity passes on a broken memory (5 of 5 runs). | case H04 |
| 3 | **A substituted value is worse than a missing one.** When the summary omitted an amount, the agent fetched it. When the defect shifted it (62.30 → 46.72), the agent used the wrong figure at the next turn — the customer was quoted a wrong fee — and corrected itself only one turn later (2 of 5 runs). | control case H05: summary text vs reply |
| 4 | **I debugged my own checks.** A literal reason-code pattern failed 4 of 5 runs on the *healthy* system because the agent wrote the code in words. I made the check tolerant to wording, removed a turn that legitimately invited mentioning the second charge, and committed a new prediction before rerunning. The main scenario now separates the defect from noise: 4/5 green on the healthy system, 0/5 under the defect. | v1 vs v2 run reports |
| 5 | **An action risk, outside memory.** On the healthy system the agent filed a dispute without the explicit "yes" it had asked for — observed three times. Text checks can't see this; it needs a check on the recorded action (the disputes table). | traces of the filing turn |

**Cost.** 180 agent turns per profile, measured at $0.17–0.19 per run, about four times the single-turn suite,
so the dialogue suite runs before a release and on changes to the compaction code, not on every commit.