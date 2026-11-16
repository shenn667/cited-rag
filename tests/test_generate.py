"""Extractive generation + refusal-gate tests."""
import re

from cited_rag.generate import (
    CITATION_RE,
    REFUSAL_TEXT,
    compute_fidelity,
    format_json_payload,
    format_text,
    generate_answer,
    select_sentences,
    split_sentences,
)


def _hits(retriever, query, k=3):
    return retriever.search(query, k=k)


def test_answer_sentences_are_verbatim_with_exact_citations(retriever):
    query = "How does BM25 ranking use term frequency saturation?"
    result = generate_answer(query, _hits(retriever, query))
    assert not result["refused"]
    assert result["fidelity"] == 1.0
    assert len(result["answer"]) == len(result["citations"])
    for sent, cite in zip(result["answer"], result["citations"]):
        assert re.fullmatch(r"[^\[\]]+", cite["file"])
        assert cite["start_line"] >= 1 and cite["end_line"] >= cite["start_line"]
        assert 0.0 <= cite["score"] <= 1.0


def test_text_output_citation_format(retriever):
    query = "cosine similarity topical overlap"
    result = generate_answer(query, _hits(retriever, query))
    text = format_text(result, k=3, min_score=0.35)
    markers = CITATION_RE.findall(text)
    assert markers, "text output must carry [file:L1-L2] citations"
    assert "Fidelity:" in text and "max_score=" in text


def test_refusal_below_min_score(retriever):
    hits = _hits(retriever, "xylophone quantum zebras marsupial")
    result = generate_answer("xylophone quantum zebras marsupial", hits,
                             min_score=0.35)
    assert result["refused"]
    assert result["citations"] == []
    text = format_text(result, k=3, min_score=0.35)
    assert text.startswith(REFUSAL_TEXT)
    assert CITATION_RE.search(text) is None, "refusals carry zero citations"


def test_refusal_on_empty_hits():
    result = generate_answer("anything", [], min_score=0.35)
    assert result["refused"]
    assert result["max_score"] == 0.0


def test_fidelity_gate_refuses_unsupported(monkeypatch, retriever):
    import cited_rag.generate as gen

    monkeypatch.setattr(
        gen, "select_sentences",
        lambda q, h, max_sentences=3: [("invented claim nowhere", h[0]["chunk"])],
    )
    result = generate_answer("query", _hits(retriever, "fusion lists"))
    assert result["refused"]
    assert result["fidelity"] < 0.5


def test_compute_fidelity_values():
    chunks = [{"text": "The cat sat. Dogs bark loudly."}]
    assert compute_fidelity(["the cat sat"], chunks) == 1.0
    assert compute_fidelity(["unrelated claim"], chunks) == 0.0
    assert compute_fidelity(["the cat sat", "unrelated"], chunks) == 0.5
    assert compute_fidelity([], chunks) == 0.0


def test_json_payload_shapes(retriever):
    ok = generate_answer("fusion combines ranked lists",
                         _hits(retriever, "fusion combines ranked lists"))
    payload = format_json_payload(ok)
    assert payload["refused"] is False
    assert isinstance(payload["answer"], list) and payload["answer"]
    assert payload["citations"] and payload["fidelity"] == 1.0

    refused = format_json_payload(generate_answer("zzz qq", [], min_score=0.9))
    assert refused == {"answer": REFUSAL_TEXT, "citations": [],
                       "fidelity": 0.0, "max_score": 0.0, "refused": True}


def test_split_sentences_basic():
    parts = split_sentences("First claim. Second claim! Third?")
    assert len(parts) == 3
    assert split_sentences("") == []


def test_select_sentences_skips_headings(retriever):
    pairs = select_sentences("BM25 ranking term frequency",
                             _hits(retriever, "BM25 ranking term frequency"))
    assert pairs
    assert all(not s.lstrip().startswith("#") for s, _ in pairs)
