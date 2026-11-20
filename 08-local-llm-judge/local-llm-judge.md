# Local LLM judge: keeping the data inside the perimeter

*Running the escalation judge on a local model so the answer text it scores never leaves the bank, and proving it still works against the same frozen set.*

**Question.** The judge in project 7 is a cloud model, which means every answer it scores , the customer's wording, the amounts, the account references , is sent to a model vendor. For a bank, that data crossing the perimeter is the problem, not the accuracy. Can the judge run on a *local* model inside the perimeter and still be trusted?

**Setup.** Same frozen 30-case calibration set as project 7, same rubric, same blind labels. Only the model changes: cloud `claude-haiku-4-5` becomes local `qwen3.5:9b` served by Ollama. The two are different vendors, so neither judge prefers its own family. This is two instruments measured on one fixed ruler , the exact discipline the whole repo is built on.

## What I built

- **A second trust statement** for the local judge in the same form as the cloud one, placed side by side so the two can be read as one comparison.
- **The interval rule, applied explicitly.** Two judges differ only if the Wilson intervals of their agreement do not overlap. If they overlap, the honest statement is "not distinguishable on this set," and the decision moves to the miss distribution.
- **A model contract**, because a local model is infrastructure: structured JSON output, a file size that fits beside the stand, a settable temperature, and a tag pinned to an immutable digest.
- **Cost in two currencies** , money and seconds-per-call on the actual hardware.
- **A one-page Model Selection Recommendation** , the decision a CTO signs without me in the room.

## Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **Lower score, but not provably worse.** The local judge agrees with my labels 0.80 (0.63–0.90) against the cloud judge's 0.97 (0.83–0.99). The Wilson intervals overlap, so on 30 cases I cannot call the local judge worse , the decision goes to the miss distribution, not the average. | both intervals, `compare_judges` |
| 2 | **The blind spot has a shape.** The local judge is noisy on two rubric triggers: it reads "I cannot do this myself" as naming an internal reason, and "within one business day" as a promised outcome. Five of its six errors are false alarms , it over-flags good answers, which for escalation is the *safe* direction , but one is a real miss. Same miss count as the cloud judge, on a different trigger. | miss distribution: 5 false alarms, 1 miss |
| 3 | **The cost moved from money to time.** The local judge is free per run but 10.9 s/call, run serially on one machine; the cloud judge is cents and sub-second, run in parallel. Money was never the deciding axis , the data perimeter was. | t_local = elapsed / calls, named hardware |
| 4 | **The model is part of the contract.** It is a "thinking" model that broke the JSON schema until I disabled reasoning; the 6.6 GB file sits just over the 6 GB target; and on a CPU without AVX-512 the runtime re-quantizes the weights on load. The tag is pinned to a digest so a library update can't silently swap the weights under a passing test. | contract table, pinned digest |
| 5 | **No fabricated evidence.** The local judge's cited `quote` was found in the answer it judged in 128 of 128 cases. Its errors are errors of judgement, not invented citations. | quote-found, full set |

**The recommendation is "move, with conditions," and the conditions are the point.** The local judge stays on the release gate, not the daily one, because 10.9 s/call is too slow to run often. It votes five times per case, because it drifts more than the cloud model. Its tag is pinned to a digest. And the whole decision rests on data residency, not accuracy , which is the honest reason to run a weaker model: the answer text stays inside the bank, and a slightly noisier judge on a frozen set is a price worth paying for that.

See the two calibration reports in this folder for the raw agreement, self-consistency and timing of each judge on the identical set.