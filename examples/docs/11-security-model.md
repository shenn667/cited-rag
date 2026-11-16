# Security Model

Four risks are audited before release. Path traversal:
indexing rejects absolute paths and `..` escapes, and only
files under the declared root are ingested. Verdict: PASS
with root-confinement tests.

Prompt injection: documents are treated as untrusted data
and rendered as quoted evidence, never as instructions to
an LLM (which is off by default in any case). Verdict: PASS.

Network exfiltration: default operation is fully offline
(stdlib only); the `--llm` adapter requires an explicit flag
and endpoint. Verdict: PASS with an offline test.

Secrets in index: the indexer warns on patterns matching
API keys and tokens (e.g. `AKIA...`, `ghp_...`) but does not
redact; operators must scrub corpora. Verdict: PASS with
documented operator responsibility.
