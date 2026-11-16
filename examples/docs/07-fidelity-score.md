# Fidelity Score

Every answer carries a fidelity score: the fraction of its
sentences supported by cited chunks. A response with 4 claims
where 3 are grounded in citations scores 0.75.

Generation is extractive by default: answer sentences are
verbatim phrases from retrieved chunks, each followed by a
citation in [file:L1-L2] format. Verbatim extraction makes
the fidelity check mechanical rather than judgment-based.

If fidelity falls below 0.5, the answer is discarded and
replaced with an explicit `Insufficient evidence` refusal.
This threshold is fixed in v0.1.0 and not user-configurable.

Fidelity and retrieval score are independent gates: a high
retrieval score with low fidelity still triggers refusal.
