# LLM as a judge: calibrating the oracle for what the agent says

*Some requirements are about wording, not data, so no code can check them. A model can, but only once you have measured it against human labels, named its blind spot, and priced the fix.*

**Question.** When the agent escalates a case to a human, the rule is about phrasing: name a real person, promise no outcome, give no internal reason. That is not deterministic, so no engine can assert it. A judge model can read the answer and rule on it, but a judge is itself a model and can be wrong. How do you know you can trust its verdict, and how do you find where it cannot be trusted?

**Setup.** The criterion is escalation (US-05 §4). The judge is `claude-haiku-4-5` (Anthropic), deliberately a different vendor from the agent under test (`gpt-5-mini`, OpenAI), so the judge is not scoring its own family and cannot prefer it. I wrote 30 cases and labeled every one PASS or FAIL myself before the judge ran even once, so the labels are blind to the judge's output. The set is split 10 obvious-PASS, 10 obvious-FAIL, 10 disputed, and the labels are committed to git before the first calibration report.

## What I built

- **A rubric of observable triggers** ([`l09_labels.jsonl`](l09_labels.jsonl)): three binary triggers, no scores. Trigger 1, a concrete human or named team is named. Trigger 2, no outcome is promised. Trigger 3, no internal reason (compliance, security) is given. The verdict carries `trigger`, `evidence_turn` and a `quote` from the answer, so every ruling points at its evidence.
- **Blind labels, frozen before the run.** 30 cases, 10 of them deliberately disputed, labeled by hand and committed before the judge saw them. Agreement is measured against those, not against a later answer.
- **Three numbers, not one.** Agreement (judge vs. my label), self-consistency (five runs, same verdict), and a Wilson 95% interval with a half-width, so a score of 0.97 is reported as 0.97 (0.83-0.99, ±0.08) and a five-case drop on 30 cases is read as noise, not collapse.
- **A fabricated-evidence check.** The judge's `quote` is substring-searched in the answer it judged. A quote that is not found means the judge invented its evidence, a different failure from a wrong verdict.
- **A fix measured on the same set,** with its price written down, and a routing rule for the class the fix cannot reach.

## Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **A high score is not trust on its own.** Agreement is 0.97 (29 of 30), self-consistency 30 of 30. What carries the trust is the rest: the interval is ±0.08, the obvious cases are 20 of 20 (so the judge agrees with the deterministic checks), and the disputed cases, the ones that actually test judgement, are 9 of 10. | Wilson interval, groups scored separately |
| 2 | **The blind spot had a direction.** Every case where the judge disagreed with me, it was more lenient: it counted vague wording ("flagged for review") as naming a human, and read an implicit promise as no promise. For escalation that is the dangerous direction, missing a mandatory escalation is worse than escalating once too often, so a lenient judge is worse than a strict one here. | miss distribution, 0 false alarms / 1 miss |
| 3 | **The fix had a price.** Tightening trigger 1 to require a concrete addressee raised agreement from 0.90 to 0.97 on the same 30 cases and removed two misses, but made the rubric longer and more PayPilot-specific (an explicit list of colleague / specialist / fraud team), so it is harder to port to another bank. A rubric change forces a full re-measurement. | v1.1 → v1.2, re-run on the frozen set |
| 4 | **One class a vote cannot catch.** The remaining miss (LB-10, "customers usually get their money back") is an implicit outcome promise, trigger 2, which the trigger 1 fix does not touch. The judge fails it stably, 5 of 5, so a "split vote goes to a human" rule never fires on it. A stable wrong verdict needs a route by case class, not by vote margin. | LB-10, 5/5 identical |
| 5 | **No fabricated evidence.** Every non-empty `quote` the judge returned was found in the answer it judged. Its errors are errors of judgement, not invented citations, which is what lets me trust the quotes while still distrusting some verdicts. | quote-found, full set |

**A judge is an instrument, not an authority.** It sits at the top of the assertion ladder for a reason: it runs only the part no engine can, the wording, and only after it has been calibrated against human labels like any other oracle. An uncalibrated judge is not an oracle, it is a second opinion. The discipline is the same as the cost work earlier in this repo: do not trust the surface number, measure it against an independent source and report the interval, not the point.