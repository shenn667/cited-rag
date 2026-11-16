"""Local JSON/SQLite index build + load (stdlib only).

JSON is the default artifact (``.cited-rag/index.json``). Paths ending in
``.db`` / ``.sqlite`` / ``.sqlite3`` use SQLite instead (same logical
content: chunks table + meta table). Both round-trip through the same
``index_to_dict`` / ``dict_to_hits`` normalized form.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time

from .chunking import (
    CHUNK_LINES,
    OVERLAP,
    chunk_file,
    find_secrets,
    iter_corpus_files,
)
from .tokenize import term_counts, tokenize

INDEX_VERSION = "0.1.0"
SQLITE_SUFFIXES = (".db", ".sqlite", ".sqlite3")


def is_sqlite_path(path: str) -> bool:
    return path.lower().endswith(SQLITE_SUFFIXES)


def build_index_data(root: str) -> tuple[dict, list[str]]:
    """Walk ``root`` and build the in-memory index dict + secret warnings."""
    entries = iter_corpus_files(root)
    chunks: list[dict] = []
    for rel, abs_path in entries:
        chunks.extend(chunk_file(abs_path, rel))

    chunk_tf: list[dict[str, int]] = []
    chunk_len: list[int] = []
    doc_freq: dict[str, int] = {}
    total_len = 0
    for chunk in chunks:
        counts = term_counts(tokenize(chunk["text"]))
        chunk_tf.append(counts)
        length = sum(counts.values())
        chunk_len.append(length)
        total_len += length
        for term in counts:
            doc_freq[term] = doc_freq.get(term, 0) + 1

    num_files = len({rel for rel, _ in entries})
    data = {
        "version": INDEX_VERSION,
        "chunk_lines": CHUNK_LINES,
        "overlap": OVERLAP,
        "chunks": chunks,
        "chunk_tf": chunk_tf,
        "chunk_len": chunk_len,
        "stats": {
            "num_files": num_files,
            "num_chunks": len(chunks),
            "avgdl": (total_len / len(chunks)) if chunks else 0.0,
            "df": doc_freq,
        },
    }

    warnings: list[str] = []
    for chunk in chunks:
        for hit in find_secrets(chunk["text"]):
            warnings.append(
                f"possible secret in {chunk['file']}:L{chunk['start_line']}: {hit}..."
            )
    return data, warnings


# ---------------------------------------------------------------- JSON ---

def save_json(data: dict, path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    os.replace(tmp, path)


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "chunks" not in data or "stats" not in data:
        raise ValueError(f"corrupt index: {path}")
    return data


# --------------------------------------------------------------- SQLite ---

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    file TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    hash TEXT NOT NULL,
    text TEXT NOT NULL,
    tf TEXT NOT NULL,
    len INTEGER NOT NULL
);
"""


def save_sqlite(data: dict, path: str) -> None:
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    try:
        con.executescript(_SQLITE_SCHEMA)
        stats = dict(data["stats"])
        meta = {
            "version": data.get("version", INDEX_VERSION),
            "chunk_lines": str(data.get("chunk_lines", CHUNK_LINES)),
            "overlap": str(data.get("overlap", OVERLAP)),
            "stats": json.dumps(stats),
        }
        con.executemany(
            "INSERT INTO meta (k, v) VALUES (?, ?)", list(meta.items())
        )
        rows = [
            (
                i,
                ch["file"],
                ch["start_line"],
                ch["end_line"],
                ch["hash"],
                ch["text"],
                json.dumps(tf),
                length,
            )
            for i, (ch, tf, length) in enumerate(
                zip(data["chunks"], data["chunk_tf"], data["chunk_len"])
            )
        ]
        con.executemany(
            "INSERT INTO chunks (id, file, start_line, end_line, hash, text, tf, len)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        con.commit()
    finally:
        con.close()


def load_sqlite(path: str) -> dict:
    con = sqlite3.connect(path)
    try:
        try:
            meta = dict(con.execute("SELECT k, v FROM meta").fetchall())
            rows = con.execute(
                "SELECT file, start_line, end_line, hash, text, tf, len"
                " FROM chunks ORDER BY id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise ValueError(f"corrupt index: {path} ({exc})") from exc
    finally:
        con.close()
    if "stats" not in meta:
        raise ValueError(f"corrupt index: {path}")
    chunks, chunk_tf, chunk_len = [], [], []
    for file, start, end, digest, text, tf_json, length in rows:
        chunks.append(
            {
                "file": file,
                "start_line": start,
                "end_line": end,
                "hash": digest,
                "text": text,
            }
        )
        chunk_tf.append(json.loads(tf_json))
        chunk_len.append(length)
    return {
        "version": meta.get("version", INDEX_VERSION),
        "chunk_lines": int(meta.get("chunk_lines", CHUNK_LINES)),
        "overlap": int(meta.get("overlap", OVERLAP)),
        "chunks": chunks,
        "chunk_tf": chunk_tf,
        "chunk_len": chunk_len,
        "stats": json.loads(meta["stats"]),
    }


# ------------------------------------------------------------ dispatch ---

def save_index(data: dict, path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    if is_sqlite_path(path):
        save_sqlite(data, path)
    else:
        save_json(data, path)


def load_index(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"index not found: {path} (run 'cited-rag index' first)")
    if is_sqlite_path(path):
        return load_sqlite(path)
    return load_json(path)


def index_corpus(root: str, index_path: str) -> dict:
    """Build the index for ``root`` and persist it. Returns a summary."""
    started = time.perf_counter()
    data, warnings = build_index_data(root)
    save_index(data, index_path)
    elapsed = time.perf_counter() - started
    size = os.path.getsize(index_path)
    return {
        "num_files": data["stats"]["num_files"],
        "num_chunks": data["stats"]["num_chunks"],
        "index_path": index_path,
        "size_bytes": size,
        "elapsed_s": elapsed,
        "warnings": warnings,
    }
