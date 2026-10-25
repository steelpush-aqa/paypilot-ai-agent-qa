## 2. RAG failure localisation

*When an answer built on retrieved documents is wrong, find where it broke — indexing, retrieval or generation —
from what the model actually received, and price each fix.*

**Question.** A wrong answer looks the same whether the index cut a table in half, the search returned too little,
or the model misused correct input. The fixes don't overlap: re-indexing, retrieval settings, a prompt change.
How do you tell them apart, and what does each one cost?

### What I built

- **Failure localisation with evidence from the retrieved fragments** — six failures (four controlled cases, two
  customer complaints) classified by where they broke, each backed by the fragment ID and the excerpt the model
  received, never by the wording of the answer.
- **A one-variable proof of cause** — the same question, prompt, model, customer and `top_k`, with only the
  index changed: recall dropped from 2 of 2 to 1 of 2 and the agent invented the missing limit.
- **A `top_k` trade-off curve** — values 3, 4, 5 and 6, three runs each, with recall, precision and measured
  input tokens per turn; chosen value and what it gives up.
- **11 retrieval cases** ([`retrieval-cases.jsonl`](02-rag-diagnostics/retrieval-cases.jsonl)) — each expected
  answer copied verbatim from a documentation row found by search, never from the agent's reply; the checked text
  chosen so a wrong answer can't match it by accident (`60` can't match `120`).

### Findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **The model's search query, not the user's language, decides retrieval.** Questions in Ukrainian and English produced the same English search query and therefore identical fragments, ranks and token counts. A retrieval loss the course expected at `top_k` 4 never happened, because it depended on a word the model never put into the query. | traces: search query per run |
| 2 | **A cheap setting that isn't.** At `top_k` 3 the needed fragment fell off the list; in one run the agent searched a second time on its own and recovered — at 8,011 input tokens, 60% more than `top_k` 4 (4,995). | three runs at each `top_k` |
| 3 | **Predicting failures from the index itself.** I rebuilt the broken index's slicing offline (newlines collapsed, cut every 160 characters) and it matched the fragments in the traces character for character — so before running, I knew which table rows were split, including one where a fee's name and its numbers landed in different fragments. | reconstruction vs trace fragments |
| 4 | **The prediction was right on the count and wrong on the mechanism.** 9 of 11 retrieval cases failed under the defect profile, close to the predicted 8 — but in 7 of them the agent never searched at all: a prompt defect told it to answer fees "from memory". One answer even quoted that instruction back to the customer. | case-by-case: search span present or absent |
| 5 | **Facts from an unmeasured source.** Asked for the list of dispute reason codes, the agent returned them in the order of the **tool schema's** enum, not the documentation's table — the list came from the tool definitions. Retrieval metrics can't see that channel. | answer order vs schema vs corpus |
| 6 | **Checks that pass wrong answers.** A rounding defect was obeyed only half-way in 2 of 5 runs: the answer gave both the exact and the rounded total, so a numeric check found the exact one and passed. And a two-fact question checked on one fact passed with the second fact invented (a daily limit of EUR 50,000 instead of 20,000). | run reports |

**Decision.** `top_k` 4: complete answers in 3 of 3 runs at the lowest cost among the complete settings. The price
is margin — the spread fragment sits at the last rank, so a differently worded query could push it out. A larger
`top_k` does not rescue a broken index: at `top_k` 5 the broken index still lost the same row, at +616 tokens.