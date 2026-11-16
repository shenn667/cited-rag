# TF-IDF Cosine Similarity in cited-rag

The second retrieval signal is TF-IDF with cosine similarity.
Each chunk is represented as a sparse vector of term weights:
tf(t, D) * idf(t), using sublinear term frequency tf = 1 + log(count).

Vectors are L2-normalized, so the cosine similarity between query
and chunk vectors is a plain dot product in [0, 1].

Preprocessing applies lowercase folding, ASCII accent stripping,
and tokenization on non-alphanumeric characters. A built-in
English stopword list (about 120 terms) is removed before weighting.

TF-IDF cosine complements BM25: BM25 rewards saturated exact
matches, while cosine captures the overall topical overlap of
the chunk. Both ranked lists are fused with Reciprocal Rank Fusion.
