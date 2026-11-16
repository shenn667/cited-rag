# cited-rag — DESIGN.md v0.1.0

## 1. Commandes

```
cited-rag index ./docs [--index .cited-rag/]
cited-rag ask "question" [--k 5] [--min-score 0.35] [--json] [--llm <adapter>]
cited-rag eval [--golden eval/golden.jsonl] [--k 5] [--json]
```

`--llm` OFF par défaut. Aucune sortie colorée obligatoire ; couleurs = accent uniquement (vert = réponse, jaune = refus, rouge = erreur).

## 2. `index` — sortie

```
Indexed 50 files → 312 chunks → .cited-rag/index.json (1.2 MB) in 12.4s
```

Erreur : `Error: ./docs not found` (exit 2). Idempotent : réindexation écrase.

## 3. `ask` — sortie texte (défaut)

```
<phrase de réponse>. [docs/deploy.md:L12-L14]
<phrase de réponse>. [docs/auth.md:L3-L5]

Fidelity: 1.00 (2/2 supported) | max_score=0.71 | k=5
```

Règles : une citation `[fichier:L1-L2]` par phrase affirmative ; offsets = lignes exactes du chunk source ; pas de phrase sans citation. En-tête/stats sur stderr ? Non : tout sur stdout, dernière ligne = `Fidelity:`.

**Refus** (si `max_score < min-score` ou fidélité < 0.5) :
```
Insufficient evidence (max_score=0.18 < min-score=0.35, k=5).
```
Aucune citation, aucune affirmation. Exit 0.

## 4. `ask` / `eval` — mode `--json`

`ask --json` :
```json
{"answer": ["phrase."], "citations": [{"file": "docs/deploy.md", "start_line": 12, "end_line": 14, "score": 0.71}], "fidelity": 1.0, "max_score": 0.71, "refused": false}
```

Refus : `{"answer": "Insufficient evidence", "citations": [], "fidelity": 0.0, "max_score": 0.18, "refused": true}`.

`eval` texte :
```
Recall@5=0.84  MRR=0.66  correct-refusal=0.90 (9/10)  n=50
```
`eval --json` : `{"recall_at_5": 0.84, "mrr": 0.66, "correct_refusal_rate": 0.9, "n": 50, "k": 5}`.

## 5. Codes d'exit

| Code | Sens |
|------|------|
| 0 | succès OU refus `Insufficient evidence` (cas nominal, pas d'erreur) |
| 1 | erreur d'exécution (index corrompu, golden illisible) |
| 2 | usage invalide (mauvais flag, dossier absent, `--k` hors [1,20]) |

## 6. Exemples

Réussi :
```
$ cited-rag ask "Où configurer le port ?" --k 5
Le port se configure dans `config.yaml` sous `server.port`. [docs/deploy.md:L12-L14]

Fidelity: 1.00 (1/1 supported) | max_score=0.71 | k=5
```

Refus :
```
$ cited-rag ask "Recette des crêpes ?"
Insufficient evidence (max_score=0.18 < min-score=0.35, k=5).
```

## 7. Acceptation design

- Test auto : chaque `[f:L1-L2]` d'un `ask` existe verbatim dans le fichier aux lignes dites.
- 10 Q hors-corpus → texte exact `Insufficient evidence`, `citations: []`, exit 0.
- `ask --json` parsable par `jq` sans erreur ; `eval` reproduit Recall@5/MRR à ±0.01.
