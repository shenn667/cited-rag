"""Optional dense/LLM adapter. OFF by default, always.

The default pipeline (BM25 + TF-IDF + RRF + extractive answers) never
touches the network. This module exists so a future dense-vector or
abstractive backend has a typed seam -- it activates only via the
explicit ``--llm`` CLI flag and never changes the citation format.
"""
from __future__ import annotations

LLM_ENABLED_BY_DEFAULT = False


def is_enabled(args) -> bool:
    """True only when the caller passed the explicit opt-in flag."""
    return bool(getattr(args, "llm", False))


def describe() -> dict:
    return {
        "name": "llm-adapter",
        "enabled_by_default": LLM_ENABLED_BY_DEFAULT,
        "status": "placeholder",
        "note": (
            "Dense vectors / abstractive generation are not bundled. "
            "Pass --llm --llm-endpoint <url> to route through an external "
            "endpoint; citation format [file:L1-L2] is unchanged."
        ),
    }
