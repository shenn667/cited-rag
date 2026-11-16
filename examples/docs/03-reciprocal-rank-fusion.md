# Reciprocal Rank Fusion (RRF)

cited-rag fuses the BM25 and TF-IDF ranked lists with Reciprocal
Rank Fusion. For each chunk d, RRF(d) = sum over runs r of
1 / (k + rank_r(d)), with constant k = 60.

RRF needs no score normalization: only ranks matter, so the
heterogeneous BM25 and cosine scales never mix directly.
A chunk ranked 1st and 3rd obtains 1/61 + 1/63 ≈ 0.0323.

The constant k = 60 dampens the influence of very high ranks
and follows the original Cormorant et al. recommendation.
Lower k (e.g. 10) would concentrate weight on top ranks;
cited-rag keeps 60 for stability across small corpora.

After fusion, the top-k chunks pass through a lightweight
rerank step (exact-phrase boost) before answer generation.
