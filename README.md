# cited-rag

[![CI](https://github.com/shenn667/cited-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/shenn667/cited-rag/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cited-rag.svg)](https://pypi.org/project/cited-rag/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![offline](https://img.shields.io/badge/offline-stdlib--only-lightgrey.svg)](https://github.com/shenn667/cited-rag)

Local RAG you can trust. Zero hallucination by design: every claim is cited
(`[file:L1-L2]`) or the answer is refused with `Insufficient evidence`.

Stdlib-only. Offline-first. No data leaves your machine unless you pass `--llm`
explicitly. Install with `pip install cited-rag` — no heavy dependencies.

## Quickstart (3 commands)

```bash
pip install cited-rag
cited-rag index ./docs --db ./index.db
cited-rag ask "how does RRF fusion work?" --k 5 --min-score 0.35
```

Ask with machine-readable output:

```bash
cited-rag ask "what is the chunk overlap?" --k 5 --json
```

Run the benchmark (reproduces the numbers below in one command):

```bash
cited-rag eval --golden eval/golden.jsonl
```

## How it works

```text
  docs (.txt/.md)
        |
   ingestion + line-based chunking (40 lines, 10 overlap, hash + line offsets)
        |
   +----+----+
   |         |
 BM25      TF-IDF/cosine        (optional dense adapter: OFF by default)
 (k1=1.5,  (sublinear tf,
  b=0.75)   stopwords, L2-norm)
   |         |
   +----+----+
        |
  Reciprocal Rank Fusion  RRF(d) = sum_r 1 / (60 + rank_r(d))
        |
  light rerank (exact-phrase boost) -> top-k
        |
  extractive generation (verbatim phrases + [file:L1-L2])
        |
  fidelity gate (>= 0.5) + min-score gate (>= 0.35)
        |
  answer  |  `Insufficient evidence` (exit 0, zero citations)
```

Why RRF: BM25 and cosine live on incompatible scales. Fusion on ranks only,
with k=60 per Cormac et al., keeps small-corpus behavior stable without tuning.

## Benchmark

Measured with `cited-rag eval --golden eval/golden.jsonl` on the bundled
corpus (12 docs in `examples/docs/`, 52 questions: 40 in-corpus + 12
out-of-corpus). Release gates (PRODUCT_BRIEF C4): Recall@5 >= 0.80,
MRR >= 0.60, correct-refusal rate >= 0.90.

| Metric | Target | Measured |
|---|---|---|
| Recall@5 | >= 0.80 | see `cited-rag eval` output |
| MRR | >= 0.60 | see `cited-rag eval` output |
| Correct-refusal (12 off-topic Q) | >= 0.90 | see `cited-rag eval` output |

Numbers are reproduced deterministically from `eval/golden.jsonl` — run the
single eval command above rather than trusting this table.

Golden format (one JSON object per line, 40 in-corpus + 12 out-of-corpus):

```json
{"question": "What are the default BM25 parameters?", "expected_doc": "01-bm25-ranking.md", "should_refuse": false}
{"question": "What is the best sourdough recipe?", "expected_doc": null, "should_refuse": true}
```

## Refusal contract

- Trigger: `max_score < --min-score` (default 0.35) or fidelity < 0.5.
- Output: the literal string `Insufficient evidence`, exit code 0.
- Guarantee: refused answers carry zero `[file:L1-L2]` markers — no invented
  citations, ever. Assert it in tests, not by inspection.

## Limitations (honest)

- Lexical retrieval only by default: BM25 + TF-IDF miss paraphrases and
  cross-lingual queries. The dense adapter (`--llm`) is opt-in and unevaluated
  against the gates above.
- Small-corpus IDF: with ~12 demo docs, rare-term statistics are noisy;
  scores stabilize as the corpus grows. Re-index after every corpus change.
- Extractive answers: verbatim quoting is faithful but stilted — no
  synthesis, no multi-hop reasoning, fixed fidelity threshold (0.5).
- Secrets: the indexer warns on key-like patterns (`AKIA...`, `ghp_...`)
  but does not redact. Scrub corpora before indexing.
- Scale: single-machine SQLite/JSON index; 50 docs index in < 60 s, but this
  is not a distributed search engine and makes no such claim.

## Project context

Third portfolio pillar after `agent-context-bridge` and `llm-eval-ci`.
See `PRODUCT_BRIEF.md` for the testable criteria (C1–C6) this release targets.

## License

MIT — see [LICENSE](LICENSE).
