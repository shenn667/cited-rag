# Optional LLM and Embeddings Adapter

Dense vectors and abstractive generation live in an optional
adapter module that is OFF by default. Stdlib-only operation
(BM25 + TF-IDF + RRF + extractive answers) is the default path.

The adapter activates only with an explicit flag:

    cited-rag ask "summarize chunking" --llm --llm-endpoint http://localhost:11434

Without `--llm`, no network call is ever made: no data leaves
the machine. Enabling the adapter never changes the citation
format; every generated sentence still requires [file:L1-L2].

Prompt injection via documents is mitigated by extractive
generation: document text is quoted, never executed as
instruction. The security audit records the verdict per risk.
