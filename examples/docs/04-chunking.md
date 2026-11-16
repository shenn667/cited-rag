# Chunking Strategy

Ingestion splits txt and md files into traceable chunks.
Each chunk records source file, start_line, end_line, and
a SHA-256 hash of its content for integrity checks.

Chunking is line-based: 40 lines per chunk with a 10-line
overlap. Markdown headings are never split from the line
that follows them, so a section title stays with its body.

Fixed overlap preserves context across boundaries: the last
10 lines of chunk N repeat as the first 10 lines of chunk N+1.
Citations therefore use exact line offsets [file:L1-L2]
verifiable against the source document.

Files outside the indexed root are rejected (path traversal
protection), and symlinks are never followed during ingestion.
