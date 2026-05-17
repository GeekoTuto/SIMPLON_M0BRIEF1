# Brief 2 — Surveiller : CI/CD, versionnement des donnees et monitoring

## Contexte du projet

La stack FastIA enrichie tourne en production (Brief 1). Mais le deploiement est encore manuel, les donnees ne sont pas versionnees, et personne ne surveille le comportement des modeles. Le CTO pose trois exigences :

> *« Premierement, plus aucune mise en production a la main — je veux une CI qui teste, build et deploie automatiquement. Deuxiemement, on doit pouvoir revenir a n'importe quelle version du dataset — la semaine derniere on a perdu 2h parce qu'on ne savait plus quel jeu avait servi a entrainer le modele en prod. Et troisiemement, je veux un tableau de bord : si le modele se degrade ou si les donnees derivent, on doit le voir avant les clients. »*

Vous allez mettre en place la **chaine de livraison continue**, le **versionnement des donnees** avec DVC, et le **monitoring operationnel** de la solution en production.

---

## Objectif principal

Industrialiser le cycle de vie de la solution FastIA : automatiser les tests et le deploiement via une pipeline CI/CD, versionner les donnees et artefacts avec DVC, et mettre en place un systeme de monitoring en production avec detection de derive et alerting.

---

## Prerequis

- Brief 1 du Module 5 complete : stack Docker Compose fonctionnelle, API enrichie, modeles enregistres dans MLflow
- Depot Git initialise avec le code source
- Compte GitHub (pour GitHub Actions)

---

## Etapes du projet

### 1. DVC — versionnement des donnees et artefacts

Initialiser DVC dans le projet et tracker les artefacts critiques :

**Initialisation :**
```bash
dvc init
```

**Fichiers a tracker :**

| Artefact | Chemin | Description |
|---|---|---|
| Dataset v1 | `data/raw/dataset_fastia_module1.jsonl` | Jeu original M1 (100 exemples) |
| Dataset v2 | `data/processed/dataset_v2.jsonl` | Jeu augmente M2 |
| Dataset v3 multi-source | `data/processed/dataset_v3_multisource.jsonl` | Jeu multi-canal M3 |
| Jeu d'evaluation langue | `data/eval/langue_eval_200.jsonl` | Benchmark M4 |
| Jeu d'evaluation sentiment | `data/eval/sentiment_eval_50.jsonl` | Benchmark M4 |
| Adaptateur LoRA | `models/fastia-classification/` | Modele fine-tune M1 |
| Modele langue | `models/fastia-language/` | Modele retenu au benchmark |
| Modele sentiment | `models/fastia-sentiment/` | Modele retenu au benchmark |

Pour chaque artefact :
- `dvc add <chemin>` — genere un fichier `.dvc` qui sera commite dans Git
- Le fichier lourd est ignore par Git (verifie `.gitignore`)

**Remote storage :**
- Configurer un remote DVC local (`dvc remote add -d local_store /tmp/dvc-store`) pour l'exercice
- Documenter la commande pour un remote S3 reel (`dvc remote add -d s3_store s3://bucket/dvc`)
- `dvc push` pour envoyer les artefacts vers le remote

**Verification :**
- Tagger la version actuelle dans Git : `git tag v3.0-multisource`
- Montrer qu'on peut **revenir a une version anterieure** : `git checkout v1.0 -- data/raw/dataset_fastia_module1.jsonl.dvc && dvc checkout`
- Documenter la procedure dans `docs/versioning.md`

### 2. GitHub Actions — pipeline CI

Creer `.github/workflows/ci.yml` :

**Declenchement :** push sur `main` et pull requests

**Jobs :**

```
ci:
  ├── lint        → ruff check src/ tests/
  ├── test        → pytest tests/ -v --tb=short
  ├── benchmark   → python scripts/run_benchmark.py --threshold
  └── build       → docker build -t fastia-api:$SHA .
```

**Etape lint :**
- Installer ruff
- Executer `ruff check src/ tests/` avec les regles configurees dans `pyproject.toml`
- Echec si violations non corrigees

**Etape test :**
- Installer les dependances (`pip install -r requirements.txt -r requirements-dev.txt`)
- Executer `pytest tests/ -v --tb=short`
- Echec si un test echoue

**Etape benchmark automatise :**
- Creer `scripts/run_benchmark.py` qui :
  - Charge les jeux d'evaluation (`langue_eval_200.jsonl`, `sentiment_eval_50.jsonl`)
  - Execute l'inference avec les modeles embarques
  - Calcule accuracy et F1 macro
  - Compare aux **seuils d'acceptation** : accuracy langue >= 0.85, F1 sentiment >= 0.70
  - Retourne un code de sortie non-zero si un seuil n'est pas atteint
  - Genere un rapport JSON (`benchmark_report.json`) uploadable comme artefact CI
- Sur une **pull request** : poster le rapport en commentaire (via `actions/github-script` ou simple `echo` dans le summary)

**Etape build :**
- `docker build -t fastia-api:${{ github.sha }} .`
- Verifier que l'image se construit sans erreur
- (Optionnel) push vers un registre

**Fichier `pyproject.toml`** — ajouter la configuration ruff :
```toml
[tool.ruff]
line-length = 120
select = ["E", "F", "W", "I"]
```

### 3. Pipeline CD — deploiement staging

Creer `.github/workflows/cd.yml` :

**Declenchement :** push sur `main` (apres merge d'une PR)

**Etapes :**
1. Build de l'image Docker avec tag `latest` + SHA
2. **Smoke test** : lancer la stack localement dans le runner (`docker compose up -d`), attendre le healthcheck, executer 3 requetes de verification :
   - `GET /health` → 200
   - `POST /predict` avec un exemple de reference → reponse contenant tous les champs enrichis
   - `GET /models` → 3 modeles listes
3. Si les smoke tests passent : marquer le deploiement comme reussi
4. **Gate humaine** pour la production : le deploiement en production reste une action manuelle documentee (`make deploy-prod`)

Documenter le flux complet dans `docs/ci_cd.md` avec un diagramme :
```
PR ouverte → CI (lint, test, benchmark) → Review → Merge → CD (build, smoke test) → Staging OK → [Manuel] Production
```

### 4. Metriques applicatives et endpoint de monitoring

Implementer `src/monitoring/metrics.py` :

**Collecteur de metriques** — un module qui accumule des compteurs et histogrammes en memoire :
- `predictions_total` : compteur total de predictions (par categorie, par langue)
- `prediction_latency_seconds` : histogramme des temps de reponse
- `enrichment_failures_total` : compteur d'echecs d'enrichissement (par tache)
- `injection_detected_total` : compteur de tentatives d'injection detectees
- `sentiment_distribution` : distribution courante des sentiments (positif/neutre/negatif)
- `language_distribution` : distribution courante des langues

**Middleware FastAPI** (`src/monitoring/middleware.py`) :
- Intercepter chaque requete sur `/predict` et `/enrich`
- Mesurer la latence
- Incrementer les compteurs
- Logger les metriques agreagees toutes les N requetes (configurable)

**Endpoint `GET /metrics`** :
- Retourne les metriques au format JSON structure :
```json
{
  "uptime_seconds": 3600,
  "predictions": {"total": 1523, "by_category": {...}, "by_language": {...}},
  "latency": {"p50": 0.12, "p95": 0.45, "p99": 1.2},
  "enrichment_failures": {"language": 3, "sentiment": 1},
  "injections_detected": 7,
  "distributions": {
    "sentiment": {"positif": 0.35, "neutre": 0.45, "negatif": 0.20},
    "language": {"fr": 0.72, "en": 0.18, "es": 0.08, "other": 0.02}
  }
}
```

**(Bonus : format Prometheus)** — si l'apprenant ajoute `prometheus-client`, exposer aussi au format Prometheus sur `GET /metrics/prometheus` pour integration Grafana.

### 5. Detection de derive (data drift)

Implementer `src/monitoring/drift.py` :

**Reference** : calculer et sauvegarder la distribution de reference a partir du jeu d'entrainement (repartition categories, langues, longueurs de texte) dans `data/reference/distributions.json`.

**Fonction de detection** :
```python
def compute_drift(reference: dict, current: dict, method: str = "psi") -> DriftReport:
    """Compare deux distributions et retourne un score de derive."""
```

- Implementer le **PSI (Population Stability Index)** :
  - PSI < 0.1 → pas de derive significative
  - 0.1 <= PSI < 0.25 → derive moderee (warning)
  - PSI >= 0.25 → derive forte (alerte)
- Appliquer sur : distribution des categories, distribution des langues, distribution des scores de confiance
- Retourner un `DriftReport` (Pydantic) : score PSI par dimension, statut global (`ok` / `warning` / `alert`), timestamp

**Endpoint `GET /monitoring/drift`** :
- Calcule le drift entre les distributions de reference et les distributions courantes (accumulees par le middleware)
- Retourne le `DriftReport`

**Script CLI `scripts/check_drift.py`** :
- Peut etre execute en cron ou dans la CI : charge les distributions depuis l'API ou la base, calcule le drift, retourne un code de sortie non-zero si alerte
- Affiche un resume textuel : `[OK] categories PSI=0.04 | [WARNING] langues PSI=0.15 | [ALERT] sentiment PSI=0.31`

### 6. Tableau de bord et alerting

**Tableau de bord Streamlit** (`src/dashboard/app.py`) :

Un dashboard operationnel en 4 panneaux :
- **Volume** : nombre de predictions par heure/jour (graphique temporel)
- **Distributions** : barplots des categories, langues, sentiments (comparaison reference vs actuel)
- **Performance** : latence p50/p95/p99, taux d'erreur d'enrichissement
- **Derive** : scores PSI par dimension, indicateur visuel (vert/orange/rouge)

Le dashboard interroge l'API (`/metrics`, `/monitoring/drift`) ou lit directement depuis PostgreSQL.

Ajouter le service au `docker-compose.yml` :
```yaml
dashboard:
  build: ./src/dashboard
  ports:
    - "8501:8501"
  depends_on:
    - api
```

**Alerting** — definir 3 alertes dans `docs/alerting.md` :

| Alerte | Condition | Severite | Action |
|---|---|---|---|
| Latence elevee | p95 > 2 secondes pendant 5 min | Warning | Verifier charge, scaling |
| Derive des donnees | PSI >= 0.25 sur une dimension | Critical | Investiguer, reentrainer |
| Taux d'erreur enrichissement | > 5% sur 100 dernieres requetes | Warning | Verifier modeles, fallback |

Pour chaque alerte, le script `scripts/check_alerts.py` :
- Interroge `/metrics` et `/monitoring/drift`
- Evalue les conditions
- Affiche le statut et retourne un code de sortie adapte
- (Bonus) envoie une notification webhook

### 7. Runbook et documentation operationnelle

**`docs/runbook.md`** — procedures pour chaque situation :

| Situation | Procedure |
|---|---|
| Modele degrade (drift alerte) | 1. Verifier `/monitoring/drift` 2. Comparer distributions 3. Si confirme : rollback modele via MLflow (`mlflow models transition --stage Production --version N-1`) 4. Ouvrir un ticket pour retrainement |
| Latence en hausse | 1. Verifier `docker stats` 2. Identifier le service en cause 3. Scaler si necessaire (`docker compose up --scale api=2`) 4. Verifier les logs d'enrichissement |
| Echec de la CI | 1. Lire le rapport de benchmark 2. Si seuil non atteint : verifier les changements de code impactant les modeles 3. Si test echoue : corriger et re-push |
| Rollback de version | 1. `git log` pour identifier la version stable 2. `git checkout <tag>` 3. `dvc checkout` 4. `make up` 5. Verifier `/health` et smoke tests |

**`docs/monitoring.md`** — guide operationnel :
- Architecture du monitoring (schema)
- Description de chaque metrique collectee
- Comment lire le dashboard
- Frequence recommandee de verification
- Comment ajouter une nouvelle metrique

**`docs/versioning.md`** — politique de versionnement :
- Code : Git + tags semantiques (`vX.Y.Z`)
- Donnees : DVC + tags Git associes
- Modeles : MLflow Model Registry (nom, version, stage)
- Correspondance : comment savoir quel dataset a entraine quel modele a quelle version

---

## Livrables

| Livrable | Description |
|---|---|
| `.github/workflows/ci.yml` | Pipeline CI (lint, test, benchmark, build) |
| `.github/workflows/cd.yml` | Pipeline CD (deploy staging, smoke tests) |
| `scripts/run_benchmark.py` | Benchmark automatise avec seuils |
| `.dvc/`, `*.dvc`, `.dvcignore` | Configuration DVC |
| `data/reference/distributions.json` | Distributions de reference pour le drift |
| `src/monitoring/metrics.py` | Collecteur de metriques applicatives |
| `src/monitoring/middleware.py` | Middleware FastAPI de collecte |
| `src/monitoring/drift.py` | Detection de derive (PSI) |
| `src/dashboard/app.py` | Tableau de bord Streamlit |
| `scripts/check_drift.py` | CLI de verification de derive |
| `scripts/check_alerts.py` | CLI de verification des alertes |
| `docs/ci_cd.md` | Documentation pipeline CI/CD avec diagramme |
| `docs/versioning.md` | Politique de versionnement (code, donnees, modeles) |
| `docs/monitoring.md` | Guide operationnel du monitoring |
| `docs/alerting.md` | Definition des 3 alertes |
| `docs/runbook.md` | Procedures operationnelles |
| `docker-compose.yml` | Mis a jour avec service dashboard |
| `pyproject.toml` | Configuration ruff |
| `README.md` | Section "Module 5 — Brief 2" |

---

## Charge de travail estimee

6 heures

---

## Ressources

- [DVC — Get Started](https://dvc.org/doc/start)
- [DVC — Data Versioning](https://dvc.org/doc/use-cases/versioning-data-and-models)
- [GitHub Actions — Quickstart](https://docs.github.com/en/actions/quickstart)
- [GitHub Actions — Docker](https://docs.github.com/en/actions/publishing-packages/publishing-docker-images)
- [Ruff — Configuration](https://docs.astral.sh/ruff/configuration/)
- [PSI — Population Stability Index](https://scholarworks.wmich.edu/dissertations/3208/)
- [Streamlit — Dashboard](https://docs.streamlit.io/)
- [prometheus-client Python](https://prometheus.github.io/client_python/)
- [MLflow — Model Registry](https://mlflow.org/docs/latest/model-registry.html)

---

## Bonus

- Ajouter un **badge CI** dans le README (`![CI](https://github.com/.../workflows/ci.yml/badge.svg)`)
- Configurer le **cache des layers Docker** dans GitHub Actions pour accelerer les builds
- Implementer un `dvc.yaml` definissant un **pipeline DVC reproductible** (stages : prepare → train → evaluate)
- Ajouter **Grafana + Prometheus** au Docker Compose en alternative au dashboard Streamlit, avec un dashboard pre-configure (`data/grafana/dashboard.json`)
- Simuler une **derive artificielle** (injecter des donnees EN dans un flux majoritairement FR) et verifier que l'alerte se declenche
- Configurer une **notification Slack** via webhook quand une alerte critique est levee
