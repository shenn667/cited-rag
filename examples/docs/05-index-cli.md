# Indexing Documents (CLI)

Build the local index with a single command:

    cited-rag index ./docs --db ./index.db

The indexer walks the directory recursively, accepts `.txt`
and `.md` files only, and stores chunks plus BM25/TF-IDF
statistics in a local JSON/SQLite index file.

Indexing 50 documents completes in under 60 seconds on a
standard machine (stdlib only, no external service).
Re-indexing is idempotent: unchanged files (same hash)
are skipped automatically.

No document content ever leaves the machine during indexing.
The index is a plain local file you can delete, copy, or
version alongside the corpus.
