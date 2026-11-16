"""Eval metrics unit tests + release-gate integration on the real corpus."""
import os

import pytest

from conftest import repo_root
from cited_rag.eval import load_golden, run_eval
from cited_rag.index import load_index


def _tiny_retriever(tmp_path):
    from cited_rag.index import build_index_data
    from cited_rag.retrieval import Retriever

    root = tmp_path / "docs"
    root.mkdir()
    (root / "alpha.md").write_text(
        "Red apples grow in orchards during autumn harvest.\n", encoding="utf-8"
    )
    (root / "beta.md").write_text(
        "Blue oceans hide submarines beneath silent waves.\n", encoding="utf-8"
    )
    data, _ = build_index_data(str(root))
    return Retriever(data)


def _write_golden(tmp_path, rows):
    import json

    golden = tmp_path / "golden.jsonl"
    golden.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return str(golden)


def test_recall_and_mrr_perfect_ranking(tmp_path):
    retriever = _tiny_retriever(tmp_path)
    golden = _write_golden(tmp_path, [
        {"question": "red apples orchards autumn harvest",
         "expected_doc": "alpha.md", "should_refuse": False},
        {"question": "blue oceans submarines silent waves",
         "expected_doc": "beta.md", "should_refuse": False},
    ])
    metrics = run_eval(retriever, golden, k=5)
    assert metrics["recall_at_5"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["n"] == 2 and metrics["k"] == 5


def test_refusal_rate_counts_correctly(tmp_path):
    retriever = _tiny_retriever(tmp_path)
    golden = _write_golden(tmp_path, [
        {"question": "quantum xylophone marsupial diplomacy",
         "expected_doc": None, "should_refuse": True},
    ])
    metrics = run_eval(retriever, golden, k=5)
    assert metrics["correct_refusal_rate"] == 1.0
    assert metrics["n_refusal"] == 1 and metrics["n_answerable"] == 0


def test_load_golden_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"question": "q"}\n')  # missing should_refuse
    with pytest.raises(ValueError):
        load_golden(str(bad))
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n")
    with pytest.raises(ValueError):
        load_golden(str(empty))
    with pytest.raises(FileNotFoundError):
        load_golden(str(tmp_path / "missing.jsonl"))


def test_release_gates_on_bundled_corpus(tmp_path):
    """PRODUCT_BRIEF C4: Recall@5>=0.80, MRR>=0.60, refusal>=0.90."""
    from cited_rag.index import build_index_data
    from cited_rag.retrieval import Retriever

    docs = os.path.join(repo_root(), "examples", "docs")
    golden = os.path.join(repo_root(), "eval", "golden.jsonl")
    assert os.path.isdir(docs), "bundled corpus missing"
    data, _ = build_index_data(docs)
    metrics = run_eval(Retriever(data), golden, k=5, min_score=0.35)
    assert metrics["n"] == 52
    assert metrics["recall_at_5"] >= 0.80, metrics
    assert metrics["mrr"] >= 0.60, metrics
    assert metrics["correct_refusal_rate"] >= 0.90, metrics


def test_llm_adapter_off_by_default():
    from cited_rag import llm_adapter

    class Args:
        pass

    assert llm_adapter.LLM_ENABLED_BY_DEFAULT is False
    assert llm_adapter.is_enabled(Args()) is False
    args = Args()
    args.llm = True
    assert llm_adapter.is_enabled(args) is True
    assert "citation" in llm_adapter.describe()["note"]
