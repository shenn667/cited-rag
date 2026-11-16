"""Traceable line-based chunking with security confinement (stdlib only).

Every chunk records ``file`` (path relative to the indexed root),
1-indexed ``start_line``/``end_line`` offsets, and a SHA-256 ``hash`` of
its exact text, so any ``[file:L1-L2]`` citation is verifiable verbatim.

Rules (PRODUCT_BRIEF C1 / DESIGN):
- line-based: 40 lines per chunk, 10-line fixed overlap;
- a markdown heading is never orphaned as the last line of a chunk;
- only ``.txt``/``.md`` files under the declared root are ingested;
- symlinks are never followed; absolute paths / ``..`` escapes rejected;
- key-like secret patterns emit warnings (never redaction).
"""
from __future__ import annotations

import hashlib
import os
import re

CHUNK_LINES = 40
OVERLAP = 10
ACCEPTED_SUFFIXES = (".txt", ".md")

# Key-like patterns worth warning about (index stores them as-is;
# the operator must scrub corpora -- see README "Limitations").
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{22,}"),
    re.compile(r"xox[bap]-[A-Za-z0-9-]+"),
    re.compile(r"sk-(live|test)-[A-Za-z0-9]{16,}"),
    re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
]


def is_heading(line: str) -> bool:
    """True for ATX markdown headings (``# ...`` up to ``###### ...``)."""
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return False
    hashes = stripped.split(" ", 1)[0] if " " in stripped else stripped
    hashes = hashes.rstrip("\n")
    return bool(hashes) and all(c == "#" for c in hashes) and len(hashes) <= 6


def chunk_text_lines(
    lines: list[str],
    source: str,
    chunk_lines: int = CHUNK_LINES,
    overlap: int = OVERLAP,
) -> list[dict]:
    """Split pre-read lines into traceable chunk dicts.

    ``lines``: file lines *without* trailing newlines. Offsets are
    1-indexed and inclusive on both ends.
    """
    if chunk_lines <= 0:
        raise ValueError("chunk_lines must be > 0")
    if not 0 <= overlap < chunk_lines:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_lines")

    chunks: list[dict] = []
    n = len(lines)
    start = 0
    while start < n:
        end = min(start + chunk_lines, n)
        # Never orphan a heading as the chunk's last line: extend the
        # boundary so the heading stays with the line that follows it.
        while end < n and is_heading(lines[end - 1]):
            end += 1
        text = "\n".join(lines[start:end])
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        chunks.append(
            {
                "file": source,
                "start_line": start + 1,
                "end_line": end,
                "hash": digest,
                "text": text,
            }
        )
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_file(
    abs_path: str,
    rel_path: str,
    chunk_lines: int = CHUNK_LINES,
    overlap: int = OVERLAP,
) -> list[dict]:
    """Read a file and chunk it. Returns [] for empty files."""
    with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    lines = content.splitlines()
    if not lines:
        return []
    return chunk_text_lines(lines, rel_path, chunk_lines, overlap)


def iter_corpus_files(root: str) -> list[tuple[str, str]]:
    """List ``(rel_path, abs_path)`` of ingestible files under ``root``.

    Sorted for determinism. Symlinks (files and dirs) are skipped,
    and any path escaping the root (traversal) is rejected.
    """
    if not os.path.isdir(root):
        raise FileNotFoundError(f"{root} not found")
    root_real = os.path.realpath(root)
    found: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Never descend into symlinked directories.
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not os.path.islink(os.path.join(dirpath, d))
        )
        for name in sorted(filenames):
            abs_path = os.path.join(dirpath, name)
            if os.path.islink(abs_path):
                continue
            if not name.lower().endswith(ACCEPTED_SUFFIXES):
                continue
            real = os.path.realpath(abs_path)
            try:
                common = os.path.commonpath([root_real, real])
            except ValueError:
                continue
            if common != root_real:
                continue
            rel = os.path.relpath(abs_path, root)
            if rel.startswith("..") or os.path.isabs(rel):
                continue
            found.append((rel, abs_path))
    return sorted(found)


def find_secrets(text: str) -> list[str]:
    """Return the matched secret-like substrings (for warnings)."""
    hits: list[str] = []
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(match.group(0)[:64])
    return hits
