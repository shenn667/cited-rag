# BM25 Ranking in cited-rag

BM25 (Best Matching 25) is the primary lexical ranker in cited-rag.
It scores chunks against the query using term frequency saturation
and inverse document frequency (IDF).

The BM25 score of a chunk D for query Q is the sum over query terms
of IDF(q) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * |D| / avgdl)).

Default parameters are k1 = 1.5 and b = 0.75. These values follow
the Robertson–Spärck Jones formulation and work well on technical
documentation without tuning.

IDF is computed over the indexed chunk collection, so adding
documents changes scores. Re-run `cited-rag index` after any
corpus change to keep IDF statistics consistent.

BM25 excels at exact term matching (error codes, function names,
CLI flags) but misses paraphrases. That is why cited-rag pairs
it with a TF-IDF cosine signal and fuses both with RRF.
