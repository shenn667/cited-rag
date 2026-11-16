# Security Audit — cited-rag v0.1.0

Scope: `src/cited_rag/` (chunking.py, index.py, retrieval.py, generate.py, cli.py, llm_adapter.py, eval.py, tokenize.py).
Method: code review + live verification (traversal probe, injection probe, import/network scan, secret-pattern scan, pytest 59 passed).
Date: 2026-11-16. Auditor: security profile.

## 1. Path traversal at indexing — PASS

- `iter_corpus_files()` (chunking.py): `os.walk(..., followlinks=False)`, symlinked dirs pruned, symlinked files skipped (`os.path.islink`), `realpath` + `commonpath` confinement check, `..`/absolute `rel` rejected, only `.txt`/`.md`.
- Verified live: corpus with `evil.md -> /etc/passwd` symlink + symlinked subdir — both excluded, only the legit file ingested.
- `cli cmd_index` rejects non-dir with exit 2; `index_corpus` errors surface as exit 1.
- Residual (Low, not blocking): a hand-crafted index DB can carry `file: ../../etc/passwd`; `ask` renders it verbatim in citations but never opens that path (retrieval reads only the index). No file-read primitive at query time.

## 2. Prompt injection via indexed documents — PASS

- Pipeline is extractive only: `generate_answer()` returns verbatim chunk sentences + `[file:L1-L2]` citations. No `eval`/`exec`/`os.system`/`subprocess`, no instruction-following step. Malicious doc text ("Ignore all previous instructions...") is either refused (no query overlap → refusal gate) or quoted verbatim with its source citation — never executed.
- Verified live: injected chunk returns quoted sentence + `evil.md:L1-L6` citation, fidelity-gated; `inspect` confirms no exec path.
- `llm_adapter` is a placeholder (no prompt construction, no tool calls); `--llm` does not change the citation format.

## 3. Offline-first by default — PASS

- Default path (`index` / `ask` / `eval` without `--llm`) imports only stdlib (`argparse, json, os, sys, re, math, hashlib, sqlite3, unicodedata, time`). Repo-wide scan: no `socket` / `urllib` / `http.client` / `requests` / `urlopen` in any module; the only "network" hit is the word in a docstring.
- `llm_adapter.LLM_ENABLED_BY_DEFAULT = False`; `is_enabled()` is true only with explicit `--llm`. With `--llm` the adapter only prints a status note via `describe()` — no endpoint call is implemented (placeholder, no URL fetch).
- `--llm-endpoint` without `--llm` is inert (flag ignored unless `llm_enabled`).
  Even with `--llm` it is silently ignored (placeholder makes no fetch) — dead
  flag: either validate/use it (https only) or reject it until wired. Low,
  no network impact today.

## 4. Secrets/PII in index or examples/docs — PASS (with operator duty)

- `SECRET_PATTERNS` (AKIA, `ghp_`, `github_pat_`, `xox[bap]-`, `sk-live/test-`, private-key header, `api_key := ...`) + `find_secrets()` emit `Warning: possible secret in file:L...` on stderr at index time; verified live for all four families.
- Design choice (documented in README Limitations + 11-security-model.md): warn, don't redact — index stores text as-is. Operator must scrub corpora. Acceptable for v0.1.0, must stay documented.
- Scan of `examples/docs/` (12 files) + `eval/golden.jsonl`: only placeholder tokens (`AKIA...`, `ghp_...`) in 11-security-model.md prose — no real keys, tokens, emails, or private keys.
- `index.json` stores relative paths only (verified head of file) — no absolute-path leakage.
- Warning text prints a 64-char secret excerpt to stderr in cleartext, which can
  persist in CI logs. Recommend masking (file+line only, or truncated hash).
  Low, documented operator duty for v0.1.0.

## Verdict

| Risk | Verdict |
|---|---|
| 1. Path traversal / symlinks | PASS |
| 2. Prompt injection via docs | PASS |
| 3. Offline-first by default | PASS |
| 4. Secrets/PII in index or examples | PASS |

No Critical/High findings. No release block. Three Low observations recorded above
(crafted-index `file` field rendered verbatim; `--llm-endpoint` dead flag;
secret excerpt in cleartext warnings) for scheduled hardening, no action required for v0.1.0.

Re-test: `~/ai_env/bin/python -m pytest tests/ -q` (59 passed); traversal/inject probes in this report re-runnable via `src/cited_rag/chunking.py::iter_corpus_files` + `generate_answer`.
