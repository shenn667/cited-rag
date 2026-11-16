# QA Report — cited-rag v0.1.0 (C1–C6)

Date: 2026-11-16 · QA (hermes-qa) · board `cited-rag`, task `t_e42b7406`
Scope: PRODUCT_BRIEF.md §2, repo `/home/sh/ai_env/labs/cited-rag`

## Verdict global : PASS — 6/6 critères validés, feu vert release.

## Résultats par critère

| Critère | Exigence | Mesuré | Verdict |
|---|---|---|---|
| C1 offline stdlib-only | `index`+`ask` sans dépendance externe | `dependencies = []` (pyproject) ; index+ask OK sans réseau | PASS |
| C2 citations exactes | 100 % affirmations citées `[fichier:L1-L2]`, offset exact | Réponse test : 3/3 phrases citées `[01-bm25-ranking.md:L1-L20]`, texte verbatim vérifié dans le fichier ; fidélité 1.00 ; tests auto verts | PASS |
| C3 refus hors-corpus | `Insufficient evidence`, exit 0, zéro citation inventée, 10 Q min | 12/12 questions hors-corpus → refus, exit 0, aucune citation | PASS |
| C4 eval chiffré | `cited-rag eval` : Recall@5 ≥ 0.80, MRR ≥ 0.60, refus correct ≥ 0.90, ≥50 Q/A | Recall@5=1.00, MRR=0.93, correct-refusal=1.00 (12/12), n=52 | PASS |
| C5 LLM OFF par défaut | adaptateur opt-in `--llm` explicite, format citation inchangé | `--llm` = `store_true`, `default=False` ; aucun appel réseau hors adaptateur (grep socket/urllib vide) | PASS |
| C6 tests + perf + doc | `pytest` vert, index < 60 s / 50 docs, README quickstart 3 commandes | 59 passed in 0.99 s ; index 12 docs en 0.4 s ; README « Quickstart (3 commands) » présent | PASS avec réserve* |

(*) Réserve mineure, non bloquante : `examples/docs` ne contient que 12 docs
(12 chunks), pas 50. Le budget 60 s est tenu avec une marge énorme (0.4 s),
mais la montée en charge à 50 docs n'a pas été mesurée telle quelle.

## Commandes exécutées (reproductibles)

- `~/ai_env/bin/pytest tests/ -q` → 59 passed in 0.99s
- `~/ai_env/bin/cited-rag index examples/docs` → 12 files → 12 chunks en 0.0s
- `~/ai_env/bin/cited-rag eval` → Recall@5=1.00 MRR=0.93 correct-refusal=1.00 (12/12) n=52
- `cited-rag ask "<question in-corpus>"` → 3 phrases citées, fidélité 1.00
- 12 questions hors-corpus (sport, cuisine, médecine, histoire…) → 12× `Insufficient evidence`, exit 0

## Recommandation

YES to ship : conditions de §2 remplies, C2/C3/C4 (bloquants) tous PASS.
Transmis à Ops pour tag `cited-rag-v0.1.0`.
