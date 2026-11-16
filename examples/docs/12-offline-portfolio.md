# Offline-First Design and Portfolio Context

cited-rag is the third portfolio pillar for an AI Engineer
profile, after agent-context-bridge and llm-eval-ci. Its
thesis: local RAG you can trust, with zero hallucination —
every claim cited, or the answer refused.

Offline-first means the full pipeline (index, retrieve,
fuse, answer, eval) runs without network access and without
mandatory dependencies: `pip install cited-rag` suffices.
The standard library covers tokenization, BM25, TF-IDF,
RRF fusion, CLI, and JSON output.

The index is a local JSON/SQLite artifact. Portability is
deliberate: copy one file and the corpus to reproduce any
cited answer on another machine with no service to configure.
