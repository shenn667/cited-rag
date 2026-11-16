"""Extractive answer generation with exact citations + refusal gate.

Every affirmative sentence is a verbatim phrase from a retrieved chunk,
followed by ``[file:L1-L2]`` with the chunk's exact line offsets.
``fidelity`` = fraction of answer sentences found verbatim in their cited
chunk (1.0 by construction). Refusal ("Insufficient evidence") fires when
``max_score < min_score`` or fidelity < 0.5, carries zero citations, and
exits 0 (nominal outcome, not an error).
"""
from __future__ import annotations

import re

from .tokenize import normalize, tokenize

FIDELITY_THRESHOLD = 0.5
REFUSAL_TEXT = "Insufficient evidence"
CITATION_RE = re.compile(r"\[([^\[\]]+):L(\d+)-L(\d+)\]")

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'“”‘’(\[]?[A-Z0-9])")


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    """Split chunk text into candidate verbatim sentences.

    Non-heading blocks are joined with spaces first so sentences wrapped
    across source lines stay whole; headings are dropped (titles, not claims).
    """
    blocks = [
        b.strip()
        for b in text.split("\n")
        if b.strip() and not b.lstrip().startswith("#")
    ]
    if not blocks:
        return []
    parts = _SENT_SPLIT_RE.split(" ".join(blocks))
    return [p.strip() for p in parts if p.strip()]


def format_citation(chunk: dict) -> str:
    return f"[{chunk['file']}:L{chunk['start_line']}-L{chunk['end_line']}]"


def compute_fidelity(sentences: list[str], chunks: list[dict]) -> float:
    """Fraction of answer sentences found verbatim in their cited chunk.

    Comparison is whitespace-insensitive (source line-wraps are joins, not
    edits), so wrapped sentences still verify against exact line offsets.
    """
    if not sentences:
        return 0.0
    normalized = [_collapse_ws(normalize(c["text"])) for c in chunks]
    supported = 0
    for sent in sentences:
        needle = _collapse_ws(normalize(sent))
        if needle and any(needle in body for body in normalized):
            supported += 1
    return supported / len(sentences)


def select_sentences(query: str, hits: list[dict], max_sentences: int = 3) -> list[tuple[str, dict]]:
    """Pick verbatim query-relevant sentences from ranked hits.

    Returns ``(sentence, chunk)`` pairs, chunk-rank ordered, deduped.
    Falls back to each hit's first sentence so an answer is never empty
    when evidence exists.
    """
    query_terms = set(tokenize(query))
    picked: list[tuple[str, dict]] = []
    seen: set[str] = set()
    fallback: list[tuple[str, dict]] = []
    for hit in hits:
        chunk = hit["chunk"]
        sentences = split_sentences(chunk["text"])
        first_body = next(
            (s for s in sentences if not s.lstrip().startswith("#")), None
        )
        if first_body and first_body not in seen:
            fallback.append((first_body, chunk))
        for sent in sentences:
            if sent.lstrip().startswith("#"):
                continue  # headings are titles, not claims
            key = normalize(sent)
            if key in seen or len(picked) >= max_sentences:
                continue
            if query_terms and not (set(tokenize(sent)) & query_terms):
                continue
            seen.add(key)
            picked.append((sent, chunk))
        if len(picked) >= max_sentences:
            break
    if not picked:
        for sent, chunk in fallback[:max_sentences]:
            if normalize(sent) not in seen:
                seen.add(normalize(sent))
                picked.append((sent, chunk))
    return picked[:max_sentences]


def generate_answer(
    query: str, hits: list[dict], min_score: float = 0.35
) -> dict:
    """Build the answer payload (refused or cited)."""
    max_score = max((h["score"] for h in hits), default=0.0)
    if not hits or max_score < min_score:
        return {
            "answer": [],
            "citations": [],
            "fidelity": 0.0,
            "max_score": max_score,
            "refused": True,
        }
    pairs = select_sentences(query, hits)
    sentences = [s for s, _ in pairs]
    chunks = [c for _, c in pairs]
    fidelity = compute_fidelity(sentences, chunks)
    if fidelity < FIDELITY_THRESHOLD or not sentences:
        return {
            "answer": [],
            "citations": [],
            "fidelity": fidelity,
            "max_score": max_score,
            "refused": True,
        }
    citations = [
        {
            "file": chunk["file"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "score": round(hit_score_for(hits, chunk), 4),
        }
        for (_, chunk) in pairs
    ]
    return {
        "answer": sentences,
        "citations": citations,
        "fidelity": round(fidelity, 4),
        "max_score": round(max_score, 4),
        "refused": False,
    }


def hit_score_for(hits: list[dict], chunk: dict) -> float:
    for hit in hits:
        if hit["chunk"] is chunk or hit["chunk"] == chunk:
            return hit["score"]
    return 0.0


def format_text(result: dict, k: int, min_score: float) -> str:
    if result["refused"]:
        return (
            f"{REFUSAL_TEXT} (max_score={result['max_score']:.2f} "
            f"< min-score={min_score:.2f}, k={k})."
        )
    lines = []
    # Re-associate sentences with citations in order.
    for sent, cite in zip(result["answer"], result["citations"]):
        lines.append(
            f"{sent} [{cite['file']}:L{cite['start_line']}-L{cite['end_line']}]"
        )
    total = len(result["answer"])
    supported = round(result["fidelity"] * total)
    lines.append(
        f"Fidelity: {result['fidelity']:.2f} ({supported}/{total} supported) "
        f"| max_score={result['max_score']:.2f} | k={k}"
    )
    return "\n".join(lines)


def format_json_payload(result: dict) -> dict:
    if result["refused"]:
        return {
            "answer": REFUSAL_TEXT,
            "citations": [],
            "fidelity": 0.0,
            "max_score": result["max_score"],
            "refused": True,
        }
    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "fidelity": result["fidelity"],
        "max_score": result["max_score"],
        "refused": False,
    }
