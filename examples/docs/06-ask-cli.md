# Asking Questions (CLI)

Query the index with:

    cited-rag ask "how does RRF fusion work?" --k 5 --min-score 0.35

The `--k` flag controls how many chunks are returned (default 5).
The `--min-score` flag sets the minimum fused score for an
acceptable answer (default 0.35).

With `--json`, the answer is emitted as machine-readable JSON
containing the response text, citations, per-chunk scores,
and the fidelity score.

Exit code is 0 even on refusal: a refusal is a normal,
expected outcome, not a crash. Scripts should check the
output payload (answer vs. refusal marker), not the exit code.
