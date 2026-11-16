# Refusal Policy: Insufficient Evidence

cited-rag refuses rather than hallucinates. When the best
fused score (max_score) is below `--min-score` (default 0.35),
the CLI prints `Insufficient evidence` with exit code 0.

No citations are invented on refusal: the output contains
zero [file:L1-L2] markers, so automated tests can assert
that refused answers carry no fabricated references.

Off-corpus questions (topics absent from the index) must
refuse at a rate of at least 0.90 on the evaluation set.
The 10 out-of-corpus questions in eval/golden.jsonl cover
cooking, sports, ancient history, and celebrity gossip.

Refusal is the third portfolio proof point alongside offline
operation and exact citations: zero hallucination by design.
