"""Hybrid retrieval unit tests."""
from cited_rag.retrieval import PHRASE_BOOST, RRF_K, Retriever, rrf_score


def test_rrf_formula():
    assert abs(rrf_score([1, 3]) - (1 / 61 + 1 / 63)) < 1e-12
    assert rrf_score([1, 1]) > rrf_score([2, 2]) > rrf_score([10, 10])


def test_bm25_ranks_exact_rare_term_first(retriever):
    scores = retriever.bm25(["zanzibar"])
    best = max(range(len(scores)), key=scores.__getitem__)
    assert retriever.chunks[best]["file"] == "doc-a.md"


def test_cosine_bounded_and_topical(retriever):
    from cited_rag.tokenize import tokenize

    scores = retriever.cosine(tokenize("cosine similarity topical overlap vectors"))
    assert all(0.0 <= s <= 1.0 for s in scores)
    best = max(range(len(scores)), key=scores.__getitem__)
    assert retriever.chunks[best]["file"] == "doc-b.md"


def test_gate_score_bounds():
    assert Retriever.gate_score(0.0, 0.0) == 0.0
    assert 0.0 < Retriever.gate_score(5.0, 0.4) < 1.0
    assert Retriever.gate_score(1e9, 1.0) <= 1.0


def test_search_returns_topk_sorted(retriever):
    hits = retriever.search("rank fusion constant sixty", k=2)
    assert len(hits) == 2
    keys = [h["rank_score"] for h in hits]
    assert keys == sorted(keys, reverse=True)
    for hit in hits:
        assert 0.0 <= hit["score"] <= 1.0
        assert {"chunk", "score", "bm25", "cosine", "rrf"} <= set(hit)


def test_search_phrase_boost_flags_verbatim(retriever):
    hits = retriever.search("Reciprocal rank fusion combines ranked lists", k=3)
    flagged = [h for h in hits if h["phrase"]]
    assert flagged, "verbatim query phrase must be detected"
    assert flagged[0]["chunk"]["file"] == "notes.txt"


def test_search_unknown_terms_scores_low(retriever):
    hits = retriever.search("xylophone quantum zebras marsupial", k=3)
    assert hits
    assert max(h["score"] for h in hits) < 0.35


def test_phrase_boost_equals_rank_one_vote():
    assert abs(PHRASE_BOOST - 1 / (RRF_K + 1)) < 1e-12
