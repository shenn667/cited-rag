# cited-rag — PRODUCT_BRIEF v0.1.0

## 1. Concept

CLI + librairie Python : `cited-rag index ./docs && cited-rag ask "question" --k 5 --min-score 0.35`.
Cible : 3e pilier portfolio Ingénieur IA (après agent-context-bridge, llm-eval-ci). RAG local fiable, zéro hallucination : toute affirmation est citée (fichier + lignes exactes) ou la réponse est refusée.

Principes : stdlib-only (aucune dépendance lourde obligatoire, `pip install cited-rag` suffit), offline-first (index local JSON/SQLite, aucune donnée ne sort sans opt-in), adaptateur LLM/embeddings optionnel et désactivé par défaut (`--llm` explicite uniquement).

Pipeline : ingestion (txt/md) → chunking traçable (chunk = fichier + `start_line`/`end_line` + hash, chevauchement fixe) → index double (BM25 + TF-IDF/cosinus, vecteurs denses via adaptateur optionnel) → fusion RRF → rerank léger → génération extractive par défaut (phrases citées verbatim) → score de fidélité par réponse (part de phrases supportées par les chunks) → refus explicite `Insufficient evidence` si `max_score < min_score` ou fidélité < seuil.

## 2. Critères testables v0.1.0

- C1 : `index` + `ask` fonctionnent offline sans dépendance externe (stdlib seule) sur jeu d'essai 50 docs.
- C2 : 100 % des affirmations d'une réponse ont une citation `[fichier:L1-L2]` vérifiable (offset exact, test automatisé).
- C3 : refus `Insufficient evidence` (exit 0, pas de citations inventées) quand `max_score < min_score` (défaut 0.35) — testé sur 10 questions hors-corpus.
- C4 : benchmark sur jeu d'essai livré (`eval/golden.jsonl`, ≥50 Q/A) : Recall@5 ≥ 0.80, MRR ≥ 0.60, taux de refus correct ≥ 0.90 sur hors-sujet. `cited-rag eval` reproduit les chiffres en une commande.
- C5 : adaptateur LLM/embeddings OFF par défaut ; activé seulement par flag explicite, sans changer le format de citation.
- C6 : `pytest` vert, `index` < 60 s sur 50 docs (machine standard), README avec quickstart en 3 commandes.

## 3. Ordres exacts aux agents

- Designer : « Produis DESIGN.md (≤1 page) : format de sortie CLI `ask` (réponse + citations + score + refus), codes couleur/exit, exemples `ask` réussi et `Insufficient evidence`. Pas de maquette web. »
- PM : « Découpe v0.1.0 en 5 tickets max sur board cited-rag (index/chunk, recherche hybride+RRF, CLI ask+refus, eval Recall@k/MRR, README/packaging), chacun avec acceptance testable reprenant C1-C6. »
- Dev : « Implémente v0.1.0 stdlib-only selon §1 : `index`, `ask --k --min-score --json`, chunking avec lignes exactes, BM25+TF-IDF+RRF, score fidélité, refus `Insufficient evidence`, `eval` sur `eval/golden.jsonl`. Adaptateur LLM en module optionnel désactivé par défaut. Preuve : `pytest` + démo CLI. »
- Security : « Audite v0.1.0 : path traversal à l'indexation (docs hors racine), injection de prompt via documents, fuite réseau (offline par défaut vérifié), secrets dans l'index. Livre verdict PASS/FAIL par risque. »
- QA : « Valide C1-C6 sur preview : matrice (offline pur, citations exactes, 10 Q hors-corpus → refus, `eval` Recall@5/MRR chiffrés, flag `--llm` off par défaut). Bloque la release si C2/C3/C4 échouent. »
- Ops : « Release v0.1.0 seulement sur feu vert QA : tag `cited-rag-v0.1.0`, build `pip install cited-rag`, publie chiffres `eval` dans les notes. Rollback = tag précédent. »
