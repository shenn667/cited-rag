"""CLI end-to-end tests (index / ask / eval, exit codes, JSON)."""
import json

import pytest

from cited_rag.cli import main
from cited_rag.generate import CITATION_RE, REFUSAL_TEXT


def _run(argv):
    """Run main(), converting SystemExit into its code."""
    try:
        return main(argv), None
    except SystemExit as exc:
        return exc.code, None


def test_index_success_and_stdout(corpus_dir, tmp_path, capsys):
    idx = str(tmp_path / ".cited-rag" / "index.json")
    code, _ = _run(["index", corpus_dir, "--index", idx])
    out = capsys.readouterr().out
    assert code == 0
    assert "Indexed 3 files" in out and "chunks" in out and idx in out


def test_index_missing_dir_exits_2(capsys):
    code, _ = _run(["index", "/nope/missing", "--index", "/tmp/x.json"])
    assert code == 2
    assert "not found" in capsys.readouterr().err


def test_ask_text_answer(json_index, capsys):
    code, _ = _run(["ask", "BM25 term frequency saturation",
                    "--index", json_index])
    out = capsys.readouterr().out
    assert code == 0
    assert CITATION_RE.search(out)
    assert "Fidelity:" in out


def test_ask_json_parseable(json_index, capsys):
    code, _ = _run(["ask", "cosine similarity overlap vectors",
                    "--index", json_index, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["refused"] is False
    assert payload["citations"] and payload["fidelity"] == 1.0
    assert 0.0 <= payload["max_score"] <= 1.0


def test_ask_refusal_exact_and_zero_citations(json_index, capsys):
    code, _ = _run(["ask", "xylophone quantum zebras marsupial",
                    "--index", json_index])
    out = capsys.readouterr().out
    assert code == 0  # refusal is nominal, not an error
    assert out.startswith(REFUSAL_TEXT)
    assert CITATION_RE.search(out) is None


def test_ask_refusal_json_shape(json_index, capsys):
    code, _ = _run(["ask", "xylophone quantum zebras marsupial",
                    "--index", json_index, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["refused"] is True
    assert payload["citations"] == [] and payload["answer"] == REFUSAL_TEXT


@pytest.mark.parametrize("bad_k", ["0", "21"])
def test_ask_invalid_k_exits_2(json_index, bad_k, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["ask", "q", "--index", json_index, "--k", bad_k])
    assert exc.value.code == 2


def test_ask_missing_index_exits_1(tmp_path, capsys):
    code, _ = _run(["ask", "hello", "--index", str(tmp_path / "no.json")])
    assert code == 1


def test_ask_llm_flag_keeps_citation_format(json_index, capsys):
    code, _ = _run(["ask", "BM25 term frequency saturation",
                    "--index", json_index, "--json", "--llm"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["refused"] is False and payload["citations"]


def test_eval_text_and_json(json_index, tmp_path, capsys):
    golden = tmp_path / "golden.jsonl"
    golden.write_text(
        '{"question": "BM25 term frequency saturation?", '
        '"expected_doc": "doc-a.md", "should_refuse": false}\n'
        '{"question": "xylophone quantum zebras?", '
        '"expected_doc": null, "should_refuse": true}\n'
    )
    code, _ = _run(["eval", "--golden", str(golden), "--index", json_index])
    out = capsys.readouterr().out
    assert code == 0
    assert "Recall@5=" in out and "MRR=" in out and "correct-refusal=" in out

    code, _ = _run(["eval", "--golden", str(golden),
                    "--index", json_index, "--json"])
    metrics = json.loads(capsys.readouterr().out)
    assert code == 0
    assert metrics["recall_at_5"] == 1.0
    assert metrics["correct_refusal_rate"] == 1.0


def test_eval_missing_golden_exits_1(json_index, tmp_path, capsys):
    code, _ = _run(["eval", "--golden", str(tmp_path / "no.jsonl"),
                    "--index", json_index])
    assert code == 1
