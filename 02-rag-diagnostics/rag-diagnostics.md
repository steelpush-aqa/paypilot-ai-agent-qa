## 2. RAG failure localisation

When an answer based on retrieved documents is wrong, the source of the failure needs to be identified: indexing, retrieval or generation. The answer alone is not enough, so the fragments actually received by the model were checked and possible fixes were compared by cost.

### What was tested

- **Six failure cases:** four controlled cases and two customer complaints. For each one, the failure category, fragment ID and excerpt passed to the model were recorded. Failures were not classified from the final wording alone.
- **A controlled index comparison:** the question, prompt, model, customer and `top_k` were kept the same while only the index was changed. Recall fell from 2 of 2 to 1 of 2, and the agent made up the missing limit.
- **A `top_k` comparison:** values 3, 4, 5 and 6 were tested, with three runs at each setting. Recall, precision and measured input tokens per turn were recorded, then cost was compared with the result.
- **11 retrieval cases** ([`retrieval-cases.jsonl`](retrieval-cases.jsonl)). Each expected answer comes directly from a documentation row found by search, not from the agent. The checked text was chosen so that a similar-looking wrong value would not pass by accident. For example, `60` must not match `120`.

### Findings

| # | What was found | Evidence |
|---|---|---|
| 1 | **The model's search query matters more than the language of the question.** Questions in Ukrainian and English produced the same English search query. They also returned the same fragments, ranks and token counts. The retrieval loss expected by the course did not happen at `top_k` 4 because the model never put the relevant word into its query. | Search query recorded in each trace |
| 2 | **The cheapest setting was not always the cheapest in practice.** At `top_k` 3, the needed fragment dropped out. In one run the agent searched again and recovered it, but that pushed input tokens to 8,011, around 60% more than `top_k` 4 at 4,995 tokens. | Three runs for each `top_k` value |
| 3 | **Some failures could be predicted by rebuilding the index.** The broken index's slicing was reproduced offline: newlines were collapsed and the text was cut every 160 characters. The result matched the trace fragments character for character. The reconstruction also showed which table rows would be split, including a fee name separated from its values. | Offline reconstruction compared with trace fragments |
| 4 | **The failure count was close to the prediction, but the cause was different.** Nine of 11 retrieval cases failed with the defect profile, close to the predicted eight. However, in seven cases, the agent never searched at all. A prompt defect told it to answer fee questions "from memory". One answer even repeated that instruction to the customer. | Checked whether each run contained a search span |
| 5 | **Some facts came from the tool schema, not the documents.** When asked for the dispute reason codes, the agent returned them in the order of the tool schema's enum, not the order in the documentation. Retrieval metrics cannot show information that came through the tool definitions instead. | Answer order compared with schema and documentation |
| 6 | **Some checks passed answers that were still wrong.** With a rounding defect, two of five runs included both the exact and rounded totals. The numeric check found the exact total and passed. Another test checked one fact in a two-fact answer, so it passed even though the agent invented a daily limit of EUR 50,000 instead of EUR 20,000. | Individual run reports |

### Decision

`top_k` 4 was selected. It produced complete answers in all three runs and was the lowest-cost setting among those that did so.

There is a trade-off: the spread fragment sits at the last rank, so a differently worded query could push it out. Increasing `top_k` does not fix a broken index either. At `top_k` 5, the broken index still lost the same row and used 616 more tokens.
