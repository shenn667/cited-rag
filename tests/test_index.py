"""Index build / persist / load tests (JSON + SQLite)."""
import json
import os

import pytest

from cited_rag.index import (
    build_index_data,
    index_corpus,
    is_sqlite_path,
    load_index,
    save_index,
)


def test_build_counts_files_and_chunks(corpus_dir):
    data, _warnings = build_index_data(corpus_dir)
    assert data["stats"]["num_files"] == 3
    assert data["stats"]["num_chunks"] == 3  # each sample doc < 40 lines
    assert data["version"] == "0.1.0"
    for chunk in data["chunks"]:
        assert {"file", "start_line", "end_line", "hash", "text"} <= set(chunk)


def test_build_is_idempotent(corpus_dir):
    first, _ = build_index_data(corpus_dir)
    second, _ = build_index_data(corpus_dir)
    assert first["chunks"] == second["chunks"]
    assert first["stats"] == second["stats"]


def test_secret_warning_emitted(corpus_dir):
    leaked = os.path.join(corpus_dir, "leak.md")
    with open(leaked, "w") as fh:
        fh.write("deploy key AKIAIOSFODNN7EXAMPLE inside\n")
    _data, warnings = build_index_data(corpus_dir)
    assert any("leak.md" in w for w in warnings)


def test_json_roundtrip(json_index, index_data):
    loaded = load_index(json_index)
    assert loaded["chunks"] == index_data["chunks"]
    assert loaded["stats"] == index_data["stats"]


def test_sqlite_roundtrip(sqlite_index, index_data):
    loaded = load_index(sqlite_index)
    assert loaded["chunks"] == index_data["chunks"]
    assert loaded["stats"]["num_chunks"] == index_data["stats"]["num_chunks"]
    assert loaded["stats"]["df"] == index_data["stats"]["df"]


def test_is_sqlite_path():
    assert is_sqlite_path("idx.db")
    assert is_sqlite_path("idx.sqlite3")
    assert not is_sqlite_path("idx.json")


def test_load_missing_index_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_index(str(tmp_path / "nope.json"))


def test_load_corrupt_index_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"hello": "world"}))
    with pytest.raises(ValueError):
        load_index(str(bad))


def test_index_corpus_summary(tmp_path, corpus_dir):
    out = str(tmp_path / "out.json")
    summary = index_corpus(corpus_dir, out)
    assert summary["num_files"] == 3
    assert summary["num_chunks"] == 3
    assert summary["index_path"] == out
    assert summary["size_bytes"] > 0
    assert summary["elapsed_s"] >= 0.0
    assert os.path.exists(out)
