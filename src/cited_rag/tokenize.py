"""Lexical preprocessing shared by BM25 and TF-IDF (stdlib only).

Pipeline: NFKD accent strip -> lowercase -> split on non-alphanumerics ->
drop stopwords -> light English stemming (plural/ing/ed + trailing-e
conflation so "score/scores/scoring" and "use/uses/using" match).
Single-character tokens (``k1``, ``b``, ``k``) are kept: they are
meaningful in this corpus (BM25 parameters, ``--k`` flag).
"""
from __future__ import annotations

import re
import unicodedata

_SPLIT_RE = re.compile(r"[^a-z0-9]+")

# Classic ~120-term English stopword list (retrieval-oriented).
STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because
    been before being below between both but by can cannot could did do does
    doing don down during each few for from further had has have having he her
    here hers herself him himself his how i if in into is it its itself like
    me more most my myself no nor not now of off on once only or other ought
    our ours ourselves out over own same she should so some such than that the
    their theirs them themselves then there these they this those through to
    too under until up very was we were what when where which while who whom
    why will with you your yours yourself yourselves s t d ll m re ve y ain
    aren couldn didn doesn hadn hasn haven isn ma mightn mustn needn shan
    shouldn wasn weren won wouldn
    """.split()
)


def normalize(text: str) -> str:
    """Lowercase + ASCII-fold (strip accents) a string."""
    folded = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return stripped.lower()


def stem(word: str) -> str:
    """Light deterministic stemmer (stdlib only, no data tables).

    Conflates plurals, ``-ing``/``-ed``/``-ly``, ``-ity``/``-able``/``-ible``
    and a trailing ``e`` so that morphological variants share one index term
    (e.g. ``score``/``scores``/``scoring`` -> ``scor``,
    ``use``/``uses``/``using`` -> ``us``,
    ``traceability``/``traceable`` -> ``trac``).
    Words of length <= 2 are returned unchanged (``k1``, ``b`` matter).
    """
    if len(word) <= 2:
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    if word.endswith("ability") and len(word) > 8:
        word = word[:-7]
    elif word.endswith("ibility") and len(word) > 8:
        word = word[:-7]
    if word.endswith("ness") and len(word) > 5:
        word = word[:-4]
    if word.endswith("ing") and len(word) > 4:
        word = word[:-3]
    elif word.endswith("ed") and len(word) > 3:
        word = word[:-2]
    elif word.endswith("ly") and len(word) > 4:
        word = word[:-2]
    if word.endswith("ity") and len(word) > 5:
        word = word[:-3]
    elif word.endswith("able") and len(word) > 5:
        word = word[:-4]
    elif word.endswith("ible") and len(word) > 5:
        word = word[:-4]
    if word.endswith("es") and len(word) > 4:
        if len(word) >= 4 and (word[-3] in "sxz" or (len(word) >= 5 and word[-4:-2] in ("ch", "sh"))):
            word = word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        word = word[:-1]
    if word.endswith("e") and len(word) > 2 and not word.endswith("ee"):
        word = word[:-1]
    return word


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    """Split text into index/query tokens (stemmed)."""
    tokens = [tok for tok in _SPLIT_RE.split(normalize(text)) if tok]
    if remove_stopwords:
        tokens = [tok for tok in tokens if tok not in STOPWORDS]
    return [stem(tok) for tok in tokens]


def term_counts(tokens: list[str]) -> dict[str, int]:
    """Count token occurrences."""
    counts: dict[str, int] = {}
    for tok in tokens:
        counts[tok] = counts.get(tok, 0) + 1
    return counts
