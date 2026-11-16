"""Shared fixtures: tiny deterministic corpus + index + retriever."""
from __future__ import annotations

import os
import sys

import pytest

# Exercise the working tree, not the installed copy.
SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))

from cited_rag.index import build_index_data, save_index  # noqa: E402
from cited_rag.retrieval import Retriever  # noqa: E402

SAMPLE_DOCS = {
    "doc-a.md": (
        "# Alpha Document\n\n"
        "The quick brown fox jumps over the lazy dog.\n"
        "BM25 ranking uses term frequency saturation.\n"
        "Zanzibar adventure begins at dawn.\n"
    ),
    "doc-b.md": (
        "# Beta Document\n\n"
        "Cosine similarity measures topical overlap of vectors.\n"
        "L2 normalization makes the dot product a cosine.\n"
        "Quantum pancakes flip in zero gravity.\n"
    ),
    "notes.txt": (
        "Reciprocal rank fusion combines ranked lists.\n"
        "The constant k equals sixty in this implementation.\n"
    ),
}


@pytest.fixture()
def corpus_dir(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    for name, text in SAMPLE_DOCS.items():
        (root / name).write_text(text, encoding="utf-8")
    return str(root)


@pytest.fixture()
def index_data(corpus_dir):
    data, _warnings = build_index_data(corpus_dir)
    return data


@pytest.fixture()
def retriever(index_data):
    return Retriever(index_data)


@pytest.fixture()
def json_index(tmp_path, index_data):
    path = str(tmp_path / "index.json")
    save_index(index_data, path)
    return path


@pytest.fixture()
def sqlite_index(tmp_path, index_data):
    path = str(tmp_path / "index.db")
    save_index(index_data, path)
    return path


def repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
