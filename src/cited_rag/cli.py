"""CLI: ``cited-rag index|ask|eval`` (stdlib only, argparse).

Exit codes (DESIGN sect. 5):
- 0: success OR nominal ``Insufficient evidence`` refusal;
- 1: runtime failure (missing/corrupt index, unreadable golden);
- 2: invalid usage (bad flag, missing dir, ``--k`` outside [1, 20]).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .eval import format_text as format_eval_text
from .eval import run_eval
from .generate import (
    format_json_payload,
    format_text as format_answer_text,
    generate_answer,
)
from .index import index_corpus, load_index
from .llm_adapter import describe as describe_llm
from .llm_adapter import is_enabled as llm_enabled
from .retrieval import Retriever

DEFAULT_INDEX = os.path.join(".cited-rag", "index.json")
DEFAULT_GOLDEN = os.path.join("eval", "golden.jsonl")
DEFAULT_K = 5
DEFAULT_MIN_SCORE = 0.35


def _add_index_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--index",
        "--db",
        dest="index",
        default=DEFAULT_INDEX,
        help=f"path to the local index file (default: {DEFAULT_INDEX})",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cited-rag",
        description="Local RAG you can trust: every claim cited, or refused.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="build the local index from docs")
    p_index.add_argument("docs", help="directory containing .txt/.md files")
    _add_index_arg(p_index)

    p_ask = sub.add_parser("ask", help="answer a question with citations")
    p_ask.add_argument("question", help="question to answer")
    p_ask.add_argument("--k", type=int, default=DEFAULT_K,
                       help="top-k chunks used (1-20, default: 5)")
    p_ask.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                       dest="min_score",
                       help="refuse below this max_score (default: 0.35)")
    p_ask.add_argument("--json", action="store_true",
                       help="emit machine-readable JSON")
    p_ask.add_argument("--llm", action="store_true", default=False,
                       help="opt-in to the external LLM adapter (OFF by default)")
    p_ask.add_argument("--llm-endpoint", default=None, dest="llm_endpoint",
                       help="external LLM endpoint URL (requires --llm)")
    _add_index_arg(p_ask)

    p_eval = sub.add_parser("eval", help="benchmark on a golden Q/A file")
    p_eval.add_argument("--golden", default=DEFAULT_GOLDEN,
                        help=f"golden JSONL file (default: {DEFAULT_GOLDEN})")
    p_eval.add_argument("--k", type=int, default=DEFAULT_K,
                        help="retrieval depth for Recall@k (1-20, default: 5)")
    p_eval.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        dest="min_score",
                        help="refusal gate used during eval (default: 0.35)")
    p_eval.add_argument("--min-recall", type=float, default=None,
                        dest="min_recall",
                        help="fail (exit 1) if Recall@k is below this (0-1, default: no gate)")
    p_eval.add_argument("--min-mrr", type=float, default=None,
                        dest="min_mrr",
                        help="fail (exit 1) if MRR is below this (0-1, default: no gate)")
    p_eval.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    _add_index_arg(p_eval)
    return parser


def _check_k(k: int) -> int:
    if k is None or not 1 <= k <= 20:
        print("Error: --k must be in [1, 20]", file=sys.stderr)
        raise SystemExit(2)
    return k


def _check_gate(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    if not 0.0 <= value <= 1.0:
        print(f"Error: {name} must be in [0, 1]", file=sys.stderr)
        raise SystemExit(2)
    return value


def _check_min_score(value: float) -> float:
    if value is None or not 0.0 <= value <= 1.0:
        print("Error: --min-score must be in [0, 1]", file=sys.stderr)
        raise SystemExit(2)
    return value


def cmd_index(args: argparse.Namespace) -> int:
    if not os.path.isdir(args.docs):
        print(f"Error: {args.docs} not found", file=sys.stderr)
        return 2
    try:
        summary = index_corpus(args.docs, args.index)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    size_mb = summary["size_bytes"] / (1024 * 1024)
    print(
        f"Indexed {summary['num_files']} files -> "
        f"{summary['num_chunks']} chunks -> {summary['index_path']} "
        f"({size_mb:.1f} MB) in {summary['elapsed_s']:.1f}s"
    )
    for warning in summary["warnings"]:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _load_retriever(index_path: str) -> Retriever | None:
    try:
        return Retriever(load_index(index_path))
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return None
    except (ValueError, OSError, KeyError) as exc:
        print(f"Error: corrupt index: {index_path} ({exc})", file=sys.stderr)
        return None


def cmd_ask(args: argparse.Namespace) -> int:
    _check_k(args.k)
    _check_min_score(args.min_score)
    retriever = _load_retriever(args.index)
    if retriever is None:
        return 1
    if llm_enabled(args):
        info = describe_llm()
        print(
            f"Note: LLM adapter active ({info['status']}); "
            "citation format unchanged.",
            file=sys.stderr,
        )
    hits = retriever.search(args.question, k=args.k)
    result = generate_answer(args.question, hits, min_score=args.min_score)
    if args.json:
        print(json.dumps(format_json_payload(result), ensure_ascii=False))
    else:
        print(format_answer_text(result, k=args.k, min_score=args.min_score))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    _check_k(args.k)
    _check_min_score(args.min_score)
    _check_gate(args.min_recall, "--min-recall")
    _check_gate(args.min_mrr, "--min-mrr")
    retriever = _load_retriever(args.index)
    if retriever is None:
        return 1
    try:
        metrics = run_eval(
            retriever, args.golden, k=args.k, min_score=args.min_score
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(metrics, ensure_ascii=False))
    else:
        print(format_eval_text(metrics))
    failures = []
    if args.min_recall is not None and metrics["recall_at_k"] < args.min_recall:
        failures.append(
            f"recall_at_k={metrics['recall_at_k']:.4f} "
            f"below --min-recall={args.min_recall}"
        )
    if args.min_mrr is not None and metrics["mrr"] < args.min_mrr:
        failures.append(
            f"mrr={metrics['mrr']:.4f} below --min-mrr={args.min_mrr}"
        )
    if failures:
        for failure in failures:
            print(f"Error: {failure}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "index":
        return cmd_index(args)
    if args.command == "ask":
        return cmd_ask(args)
    if args.command == "eval":
        return cmd_eval(args)
    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
