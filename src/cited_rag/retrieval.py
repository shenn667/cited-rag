"""Hybrid retrieval: BM25 + TF-IDF/cosine fused with RRF (stdlib only).

- BM25: Robertson-Sparck Jones, ``k1=1.5``, ``b=0.75``,
  ``idf(t) = ln(1 + (N - df + 0.5) / (df + 0.5))``.
- TF-IDF: sublinear tf ``1 + ln(count)``, ``idf(t) = ln(1 + N / df)``,
  L2-normalized vectors, cosine = dot product in [0, 1].
- Fusion: Reciprocal Rank Fusion, ``RRF(d) = sum_r 1 / (60 + rank_r(d))``.
- Rerank: exact-query-phrase boost (one rank-1-equivalent step) plus
  stemmed-bigram overlap boost (0.3 for one shared bigram, 0.5 for 2+).
- Gate score (``max_score``): ``0.4 * cosine + 0.4 * coverage + 0.5 * bonus``
  in [0, 1], where coverage is the IDF-weighted fraction of distinct query
  terms present in the chunk. Ranking uses RRF; the gate score measures
  absolute relevance so off-corpus queries refuse while paraphrased
  in-corpus questions still pass (calibrated: in-corpus >= 0.39,
  off-corpus <= 0.15 on the bundled 12-doc corpus, threshold 0.35).
"""
from __future__ import annotations

import math

from .tokenize import normalize, term_counts, tokenize

BM25_K1 = 1.5
BM25_B = 0.75
RRF_K = 60
# Saturation constant for the legacy BM25 gate component (kept for API
# compatibility; search() now uses the fused coverage gate below).
SCORE_BETA = 6.0
# Exact-phrase rerank boost == one rank-1 RRF vote: stable, scale-free.
PHRASE_BOOST = 1.0 / (RRF_K + 1)


def rrf_score(ranks: list[int], k: int = RRF_K) -> float:
    """Reciprocal Rank Fusion over 1-based ranks from each run."""
    return sum(1.0 / (k + r) for r in ranks)


def _bigrams(tokens: list[str]) -> set[str]:
    return set(" ".join(tokens[i:i + 2]) for i in range(len(tokens) - 1))


def _bigram_bonus(query_bi: set[str], doc_bi: set[str]) -> float:
    overlap = len(query_bi.intersection(doc_bi))
    if overlap >= 2:
        return 0.5
    if overlap >= 1:
        return 0.3
    return 0.0


class Retriever:
    def __init__(self, index: dict):
        self.index = index
        self.chunks: list[dict] = index["chunks"]
        self.chunk_tf: list[dict[str, int]] = index["chunk_tf"]
        self.chunk_len: list[int] = index["chunk_len"]
        stats = index["stats"]
        self.num_chunks = stats["num_chunks"]
        self.avgdl = stats["avgdl"] or 1.0
        self.df: dict[str, int] = stats["df"]
        self._norms = [self._tfidf_norm(tf) for tf in self.chunk_tf]
        # Precompute stemmed bigram sets for the rerank bonus.
        self._chunk_bigrams: list[set[str]] = []
        for chunk in self.chunks:
            try:
                self._chunk_bigrams.append(_bigrams(tokenize(chunk["text"])))
            except Exception:
                self._chunk_bigrams.append(set())

    # -- IDFs ---------------------------------------------------------
    def idf_bm25(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1.0 + (self.num_chunks - df + 0.5) / (df + 0.5))

    def idf_tfidf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1.0 + self.num_chunks / (df + 1e-9))

    def _idf_coverage(self, term: str) -> float:
        df = self.df.get(term, 0)
        if df == 0:
            return math.log(1.0 + self.num_chunks / 0.5)
        return math.log(1.0 + self.num_chunks / df)

    @staticmethod
    def _sublinear_tf(count: int) -> float:
        return 1.0 + math.log(count) if count > 0 else 0.0

    def _tfidf_norm(self, tf: dict[str, int]) -> float:
        return math.sqrt(
            sum(
                (self._sublinear_tf(c) * self.idf_tfidf(t)) ** 2
                for t, c in tf.items()
            )
        )

    # -- scorers ------------------------------------------------------
    def bm25(self, query_terms: list[str]) -> list[float]:
        qtf = term_counts(query_terms)
        scores = [0.0] * self.num_chunks
        for i, tf in enumerate(self.chunk_tf):
            dl = self.chunk_len[i] or 1
            total = 0.0
            for term in qtf:
                count = tf.get(term, 0)
                if not count:
                    continue
                idf = self.idf_bm25(term)
                denom = count + BM25_K1 * (
                    1.0 - BM25_B + BM25_B * dl / self.avgdl
                )
                total += idf * count * (BM25_K1 + 1.0) / denom
            scores[i] = total
        return scores

    def cosine(self, query_terms: list[str]) -> list[float]:
        # Terms absent from the index carry no signal: drop them instead of
        # assigning a near-infinite unseen IDF that would drown the score.
        qtf = term_counts(t for t in query_terms if t in self.df)
        if not qtf:
            return [0.0] * self.num_chunks
        qweights = {
            t: self._sublinear_tf(c) * self.idf_tfidf(t) for t, c in qtf.items()
        }
        qnorm = math.sqrt(sum(w * w for w in qweights.values()))
        if qnorm == 0.0:
            return [0.0] * self.num_chunks
        scores = []
        for i, tf in enumerate(self.chunk_tf):
            dot = sum(
                qweights[t] * self._sublinear_tf(tf.get(t, 0)) * self.idf_tfidf(t)
                for t in qweights
                if tf.get(t, 0)
            )
            cnorm = self._norms[i]
            scores.append(dot / (qnorm * cnorm) if cnorm else 0.0)
        return scores

    def coverage(self, query_terms: list[str], chunk_id: int) -> float:
        """IDF-weighted fraction of distinct query terms in the chunk."""
        uniq = set(query_terms)
        if not uniq:
            return 0.0
        chunk_terms = set(self.chunk_tf[chunk_id].keys())
        num = sum(self._idf_coverage(t) for t in uniq if t in chunk_terms)
        den = sum(self._idf_coverage(t) for t in uniq)
        return num / den if den else 0.0

    @staticmethod
    def gate_score(bm25: float, cosine: float) -> float:
        """Absolute relevance in [0, 1] for the refusal gate (legacy)."""
        bm_norm = bm25 / (bm25 + SCORE_BETA) if bm25 > 0 else 0.0
        return 0.5 * bm_norm + 0.5 * min(1.0, max(0.0, cosine))

    def fused_score(self, cosine: float, coverage: float, bonus: float) -> float:
        """Coverage-aware gate score in [0, 1] used as ``max_score``."""
        val = 0.4 * max(0.0, min(1.0, cosine)) + 0.4 * max(0.0, min(1.0, coverage)) + 0.5 * bonus
        return max(0.0, min(1.0, val))

    # -- search -------------------------------------------------------
    @staticmethod
    def _rank_order(scores: list[float]) -> list[int]:
        """Chunk ids sorted by descending score (stable)."""
        return sorted(range(len(scores)), key=lambda i: (-scores[i], i))

    @staticmethod
    def _rank_positions(order: list[int]) -> dict[int, int]:
        """Map chunk id -> 1-based rank."""
        return {cid: rank + 1 for rank, cid in enumerate(order)}

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Hybrid search: BM25 + cosine -> RRF -> phrase/bigram rerank -> top-k."""
        query_terms = tokenize(query)
        bm = self.bm25(query_terms)
        cos = self.cosine(query_terms)
        order_bm = self._rank_order(bm)
        order_cos = self._rank_order(cos)
        pos_bm = self._rank_positions(order_bm)
        pos_cos = self._rank_positions(order_cos)

        query_norm = normalize(query)
        query_bi = _bigrams(query_terms)
        hits = []
        for cid, chunk in enumerate(self.chunks):
            rrf = rrf_score([pos_bm[cid], pos_cos[cid]])
            phrase = query_norm in normalize(chunk["text"])
            bonus = _bigram_bonus(query_bi, self._chunk_bigrams[cid])
            rank_score = rrf * (1.0 + bonus) + (PHRASE_BOOST if phrase else 0.0)
            cov = self.coverage(query_terms, cid)
            score = self.fused_score(cos[cid], cov, bonus)
            if phrase:
                score = min(1.0, score + 0.05)
            hits.append(
                {
                    "chunk": chunk,
                    "score": score,
                    "rank_score": rank_score,
                    "bm25": bm[cid],
                    "cosine": cos[cid],
                    "coverage": cov,
                    "bonus": bonus,
                    "rrf": rrf,
                    "phrase": phrase,
                }
            )
        hits.sort(key=lambda h: (-h["rank_score"], -h["score"]))
        return hits[: max(0, k)]
