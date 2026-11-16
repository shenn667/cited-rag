"""One-command benchmark over eval/golden.jsonl (stdlib only).

Metrics:
- Recall@k: fraction of answerable questions whose ``expected_doc``
  (basename match) appears in the top-k retrieved chunk files.
- MRR: mean of 1/rank of the first relevant chunk (answerable only).
- correct-refusal rate: fraction of ``should_refuse`` questions for which
  the full ask pipeline (search + generate + min_score gate) refuses.
"""
from __future__ import annotations

import json
import os

from .generate import generate_answer
from .retrieval import Retriever


def load_golden(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"golden file not found: {path}")
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON ({exc})") from exc
            if "question" not in rec or "should_refuse" not in rec:
                raise ValueError(f"{path}:{lineno}: missing question/should_refuse")
            records.append(rec)
    if not records:
        raise ValueError(f"golden file is empty: {path}")
    return records


def _basename(path: str | None) -> str | None:
    if not path:
        return None
    return os.path.basename(path)


def run_eval(
    retriever: Retriever,
    golden_path: str,
    k: int = 5,
    min_score: float = 0.35,
) -> dict:
    records = load_golden(golden_path)
    n_answerable = 0
    n_refusal = 0
    recall_hits = 0
    reciprocal_sum = 0.0
    correct_refusals = 0

    for rec in records:
        question = rec["question"]
        if rec.get("should_refuse"):
            n_refusal += 1
            hits = retriever.search(question, k=k)
            result = generate_answer(question, hits, min_score=min_score)
            if result["refused"]:
                correct_refusals += 1
        else:
            n_answerable += 1
            expected = _basename(rec.get("expected_doc"))
            hits = retriever.search(question, k=k)
            rank = None
            for i, hit in enumerate(hits, 1):
                if _basename(hit["chunk"]["file"]) == expected:
                    rank = i
                    break
            if rank is not None:
                recall_hits += 1
                reciprocal_sum += 1.0 / rank

    recall = recall_hits / n_answerable if n_answerable else 0.0
    mrr = reciprocal_sum / n_answerable if n_answerable else 0.0
    refusal_rate = correct_refusals / n_refusal if n_refusal else 1.0
    return {
        "recall_at_k": round(recall, 4),
        f"recall_at_{k}": round(recall, 4),
        "mrr": round(mrr, 4),
        "correct_refusal_rate": round(refusal_rate, 4),
        "correct_refusals": correct_refusals,
        "n_refusal": n_refusal,
        "n_answerable": n_answerable,
        "n": len(records),
        "k": k,
    }


def format_text(metrics: dict) -> str:
    k = metrics["k"]
    recall = metrics["recall_at_k"]
    return (
        f"Recall@{k}={recall:.2f}  MRR={metrics['mrr']:.2f}  "
        f"correct-refusal={metrics['correct_refusal_rate']:.2f} "
        f"({metrics['correct_refusals']}/{metrics['n_refusal']})  "
        f"n={metrics['n']}"
    )
