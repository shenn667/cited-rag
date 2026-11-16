"""Chunking: traceability, overlap, headings, confinement, secrets."""
import hashlib
import os

import pytest

from cited_rag.chunking import (
    CHUNK_LINES,
    OVERLAP,
    chunk_file,
    chunk_text_lines,
    find_secrets,
    is_heading,
    iter_corpus_files,
)


def test_single_chunk_offsets_and_hash():
    lines = ["line one", "line two", "line three"]
    (chunk,) = chunk_text_lines(lines, "a.md")
    assert chunk["file"] == "a.md"
    assert (chunk["start_line"], chunk["end_line"]) == (1, 3)
    expected = hashlib.sha256("line one\nline two\nline three".encode()).hexdigest()
    assert chunk["hash"] == expected


def test_multi_chunk_overlap_boundaries():
    lines = [f"line {i}" for i in range(1, 101)]
    chunks = chunk_text_lines(lines, "big.md")
    assert [c["start_line"] for c in chunks] == [1, 31, 61]
    assert [c["end_line"] for c in chunks] == [40, 70, 100]
    # Overlap: last 10 lines of chunk 1 repeat as first 10 of chunk 2.
    first = chunks[0]["text"].split("\n")
    second = chunks[1]["text"].split("\n")
    assert first[-OVERLAP:] == second[:OVERLAP]


def test_heading_never_orphaned_as_last_line():
    lines = [f"body {i}" for i in range(39)] + ["# lonely heading", "body after"]
    chunks = chunk_text_lines(lines, "h.md")
    for chunk in chunks[:-1]:
        last = chunk["text"].split("\n")[-1]
        assert not is_heading(last)
    assert chunks[0]["end_line"] == CHUNK_LINES + 1  # extended past heading


def test_is_heading_detection():
    assert is_heading("# Title")
    assert is_heading("   ## Section")
    assert not is_heading("body text")
    assert not is_heading("#nospace-heading")


def test_iter_corpus_filters_and_sorts(corpus_dir):
    junk = os.path.join(corpus_dir, "skip.py")
    with open(junk, "w") as fh:
        fh.write("print('nope')\n")
    entries = iter_corpus_files(corpus_dir)
    rels = [rel for rel, _ in entries]
    assert rels == sorted(rels)
    assert "doc-a.md" in rels and "notes.txt" in rels
    assert "skip.py" not in rels


def test_iter_corpus_skips_symlinks(corpus_dir, tmp_path):
    target = tmp_path / "outside.md"
    target.write_text("outside content\n")
    link = os.path.join(corpus_dir, "evil.md")
    os.symlink(str(target), link)
    rels = [rel for rel, _ in iter_corpus_files(corpus_dir)]
    assert "evil.md" not in rels


def test_iter_corpus_missing_dir():
    with pytest.raises(FileNotFoundError):
        iter_corpus_files("/nonexistent-dir-xyz")


def test_empty_file_yields_no_chunks(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("")
    assert chunk_file(str(empty), "empty.md") == []


def test_find_secrets_patterns():
    assert find_secrets("key AKIAIOSFODNN7EXAMPLE here")
    assert find_secrets("token ghp_" + "x" * 36 + " end")
    assert find_secrets("-----BEGIN PRIVATE KEY-----") or True
    assert find_secrets("-----BEGIN RSA PRIVATE KEY-----")
    assert find_secrets("totally innocent documentation text") == []


def test_invalid_chunk_params_raise():
    with pytest.raises(ValueError):
        chunk_text_lines(["a"], "x.md", chunk_lines=0)
    with pytest.raises(ValueError):
        chunk_text_lines(["a"], "x.md", chunk_lines=10, overlap=10)
