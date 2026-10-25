## 2. RAG failure localisation

A wrong answer based on retrieved documents can come from the index, retrieval, or the model's use of the retrieved text. The investigation focused on finding where each failure started, then comparing fixes against both answer quality and token cost.

### Experiments

Six failures were investigated: four controlled cases and two customer complaints. For each, the failure category, fragment ID, and excerpt passed to the model were recorded. Eleven additional cases in [`retrieval-cases.jsonl`](retrieval-cases.jsonl) check answers against the source documentation.

Two experiments helped separate the possible causes:

| Experiment | What changed | Result |
|---|---|---|
| Index comparison | Only the index changed; question, prompt, model, customer and `top_k` stayed the same. | Recall fell from 2/2 to 1/2, and the agent invented the missing limit. |
| `top_k` comparison | Values 3, 4, 5 and 6 were tested, with three runs at each setting. Recall, precision and input tokens were recorded. | `top_k` 4 gave complete answers in all three runs at lower cost than the other complete settings. More detail is below. |

### Choosing a retrieval setting

| Setting | Observed result | Trade-off |
|---|---|---|
| `top_k` 3 | The needed fragment dropped out. In one run the agent searched again and recovered it, but input usage rose to 8,011 tokens. | Around 60% more input tokens than `top_k` 4 in the comparison run. |
| `top_k` 4 | Complete answers in all three runs, at 4,995 input tokens in the comparison run. | Lowest-cost setting among those that returned complete answers in all three runs. |
| `top_k` 5 | With the broken index, the same row was still missing and 616 more tokens were used than at `top_k` 4. | Increasing `top_k` does not repair a broken index. |
| `top_k` 6 | Included in the three-run comparison. | No separate token figure is stated here. |

Based on these runs, `top_k` 4 was selected. There is still a trade-off: the spread fragment sits at the last rank, so a differently worded query could push it out.

### What the traces revealed

| Finding | Evidence and consequence |
|---|---|
| **Question language did not change the search.** Ukrainian and English questions produced the same English query, fragments, ranks and token counts. | The retrieval loss expected by the course did not happen at `top_k` 4 because the relevant word never appeared in the model's query. |
| **The index defect could be reproduced.** Newlines were collapsed and text was cut every 160 characters. | An offline reconstruction matched the trace fragments character for character and showed table rows split between a fee name and its values. |
| **The failure count was close to the prediction, but the cause differed.** Nine of 11 retrieval cases failed with the defect profile, close to the predicted eight. | In seven cases the agent never searched. A prompt defect told it to answer fee questions "from memory"; one answer repeated that instruction to the customer. |
| **Some facts came from the tool schema, not the documents.** The agent returned dispute reason codes in the schema's enum order rather than the documentation order. | Retrieval metrics alone cannot reveal information supplied through tool definitions. |
| **Some assertions passed wrong answers.** With a rounding defect, two of five runs included both exact and rounded totals, so the numeric check found the exact total and passed. Another test checked one fact in a two-fact answer and passed despite an invented daily limit of EUR 50,000 instead of EUR 20,000. | The assertions needed to check the relationship between facts, not just the presence of one correct number. |

The selected setting is a cost and coverage trade-off, not a fix for every failure. The index and prompt defects need separate corrections; increasing `top_k` alone will not address them.
