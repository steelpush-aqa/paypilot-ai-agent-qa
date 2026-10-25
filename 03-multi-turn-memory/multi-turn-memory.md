# Multi-turn memory

The test followed a customer dispute across a conversation that switches topics before returning to the original payment. The key question was when the details disappeared from the model's context, and when that loss began to affect the answer.

### Scenario and test design

The customer reports that goods from a 240.00 EUR card payment never arrived. Questions about the card limit and FX spread interrupt the dispute discussion. The stand summarises the conversation after two turns. In the defect profile, the summary can drop numbers (D06) or replace them with other values (D07).

Five dialogue cases in [\`l05_dialogs.jsonl\`](l05_dialogs.jsonl) cover different conversation lengths, numbers of case details and topic changes. The checks look for the expected value and forbid likely substitutions, such as the second identical charge or a different reason code. Expected values come from the bank's engine rather than the agent's earlier reply.

> The \`plan_role\` values are in Ukrainian because the course loader accepts only those labels: \`основний\` means main, \`найгірший\` means worst case, \`контроль\` means control, and \`ізоляція осі\` means axis isolation.

### Failure timeline

**Turns 1–2: The dispute details are established.** The customer identifies transaction TX-0401 for 240.00 EUR and explains that the goods never arrived.

**After turn 2: The conversation is summarised.** The compaction code creates the summary at threshold + 1. In the defect runs, important details are missing from the model's input at turn 3 in all five runs.

**Turns 3–4: The problem is not obvious yet.** The customer asks about the card limit and FX spread. The replies look normal, even though the summary has already lost details.

**Turn 5: The memory failure becomes visible.** The agent calls \`get_transactions\` and recovers the amount, so an amount-only check passes. However, it no longer knows which of two identical 240.00 EUR charges is being disputed. In all five runs, checking only the amount missed the problem.

**A separate substitution case: A wrong value leads to a wrong fee.** When the summary changed 62.30 to 46.72, the agent used the wrong figure and quoted the customer the wrong fee. It corrected itself one turn later in two of five runs.

### What needed changing in the tests

The first reason-code assertion failed in four of five clean runs because the agent expressed the code in words rather than using the literal code. The assertion was adjusted to allow wording differences. A turn that could reasonably prompt a mention of the second charge was removed, and a new prediction was recorded before rerunning.

After those changes, the main scenario passed four of five clean runs and zero of five runs with the defect enabled. The clean-system failures were not hidden; the assertion was changed because it was checking wording rather than the underlying fact.

### A separate action risk

On the clean system, the agent filed a dispute without the explicit confirmation it had asked for. This happened three times. A text-only check would not be enough to catch it: the test needs to inspect the action recorded in the disputes table.

### Cost and when to run it

The dialogue suite uses 180 agent turns per profile and costs about $0.17 to $0.19 per run, roughly four times the single-turn suite. It is better suited to pre-release checks and to runs triggered by changes to conversation compaction than to every commit.
