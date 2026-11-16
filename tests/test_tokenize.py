"""Tokenization unit tests."""
from cited_rag.tokenize import STOPWORDS, normalize, term_counts, tokenize


def test_normalize_lowercase_and_accents():
    assert normalize("Café RÉSUMÉ naïve") == "cafe resume naive"


def test_stopwords_removed():
    assert tokenize("the cat sat on the mat") == ["cat", "sat", "mat"]


def test_keeps_single_char_technical_tokens():
    tokens = tokenize("default BM25 parameters k1 and b")
    assert "k1" in tokens
    assert "b" in tokens
    assert "bm25" in tokens


def test_empty_string_tokenizes_empty():
    assert tokenize("") == []
    assert tokenize("the and of") == []


def test_term_counts():
    assert term_counts(["a", "b", "a"]) == {"a": 2, "b": 1}
    assert term_counts([]) == {}


def test_stopword_list_has_expected_size():
    assert len(STOPWORDS) >= 100
