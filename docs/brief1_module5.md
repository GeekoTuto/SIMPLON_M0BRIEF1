# Brief 1 — Deployer : implementation, conteneurisation et registre de modeles

## Contexte du projet

Le dossier de conception du Module 4 a ete valide par le CTO : architecture cible, spec API, migration SQL, model cards, plan de securite. Tout est documente, rien n'est deploye. Le CTO est clair :

> *« Le dossier est solide, mais un diagramme Mermaid ne repond pas aux tickets clients. Je veux que la pipeline enrichie tourne en production d'ici la fin de la semaine. Un `docker compose up` et tout demarre : la base, l'API enrichie, le tracking MLflow. Et chaque modele doit etre versionne — si on doit rollback vendredi soir, je veux pouvoir le faire en une commande. »*

Vous allez **implementer le plan de mise en oeuvre** du M4 (les 3 phases), deployer la stack complete via Docker Compose, et enregistrer les modeles dans le registre MLflow.

---

## Objectif principal

Transformer le dossier de conception M4 en une stack de production fonctionnelle : implementer les enrichissements (langue, sentiment, routage), mettre a jour l'API, conteneuriser l'ensemble, et versionner les modeles via MLflow Model Registry.

---

## Prerequis

- Module 4 complete : dossier de conception, input sanitizer, schemas Pydantic, migration SQL
- Docker et Docker Compose installes
- Pipeline FastIA M3 fonctionnelle (API, base PostgreSQL, pipeline multi-source)

---

## Etapes du projet

### 1. Appliquer la migration SQL

Appliquer la migration preparee au M4 (`docs/migration_enrichment.sql` ou via Alembic) :

| Colonne | Type | Description |
|---|---|---|
| `langue` | `VARCHAR(5)` | Code ISO 639-1 |
| `langue_confidence` | `FLOAT` | Score de confiance [0, 1] |
| `sentiment` | `VARCHAR(10)` | `positif`, `neutre`, `negatif` |
| `sentiment_score` | `FLOAT` | Score de confiance |
| `enriched_at` | `TIMESTAMPTZ` | Date d'enrichissement |
| `routed_priority` | `VARCHAR(20)` | `high_intl`, `high_negative`, `normal` |

- Executer la migration sur la base existante
- Verifier que les donnees existantes ne sont pas impactees (colonnes nullable)
- Creer l'index `idx_demandes_langue` sur la colonne `langue`
- Documenter la migration dans le README

### 2. Implementer les enrichissements production-ready

Transformer le PoC du M3 (`src/pipeline/enrich.py`) en modules de production :

**`src/pipeline/enrich_language.py`** :
- Charger le modele retenu au benchmark M4 (langdetect, fasttext ou XLM-RoBERTa selon la recommandation)
- Implementer un **cache par hash** du body : si le texte a deja ete enrichi, retourner le resultat stocke sans re-inferer
- Gerer le **fallback** : si le modele echoue ou si la confiance est sous un seuil configurable (defaut 0.5), retourner `langue=None` sans bloquer la pipeline
- Logger chaque enrichissement avec Loguru (texte tronque, resultat, temps d'inference)

**`src/pipeline/enrich_sentiment.py`** :
- Charger le modele de sentiment retenu
- Appliquer **uniquement sur les textes FR** (ou selon la langue detectee a l'etape precedente)
- Mapper les sorties brutes du modele vers `positif/neutre/negatif` (documenter le mapping)
- Meme pattern : cache, fallback, logging

**`src/pipeline/route.py`** :
- Implementer la logique de routage prioritaire :
  - `langue != 'fr'` → `high_intl`
  - `sentiment == 'negatif'` et `sentiment_score > 0.8` → `high_negative`
  - sinon → `normal`
- Retourner un objet `RoutingDecision` (Pydantic) avec la priorite et la justification

**Integration dans la pipeline** :
- Modifier `src/pipeline/run.py` pour chainer : cleaning → sanitize (M4) → enrich_language → enrich_sentiment → route → stockage
- L'enrichissement doit etre **idempotent** : relancer la pipeline sur une ligne deja enrichie ne doit pas la re-traiter (sauf flag `--force`)

### 3. Mettre a jour l'API FastAPI

Implementer les endpoints definis dans `docs/spec_api_enrichie.md` (M4) :

**`POST /predict`** — reponse enrichie :
```json
{
  "categorie": "reclamation",
  "priorite": "haute",
  "reponse_suggeree": "...",
  "langue": "fr",
  "langue_confidence": 0.97,
  "sentiment": "negatif",
  "sentiment_score": 0.82,
  "routed_priority": "high_negative",
  "sanitization": {
    "injection_suspected": false,
    "homoglyphs_replaced": 0
  }
}
```

**`POST /enrich`** — enrichissement seul (sans classification) :
- Entree : `{"text": "..."}`
- Sortie : `{"langue": "...", "langue_confidence": ..., "sentiment": "...", "sentiment_score": ...}`

**`GET /models`** — liste des modeles actifs :
- Retourne nom, version, tache, stage (Staging/Production), date de chargement

**`GET /models/{task}/metrics`** — metriques du dernier benchmark :
- Retourne accuracy, F1, date du benchmark, nombre d'exemples

Utiliser les schemas Pydantic definis dans `src/api/schemas.py` (M4 B2).

Integrer le `input_sanitizer` (M4 B2) dans le flux `/predict` et `/enrich` : chaque texte entrant passe par `sanitize()` avant tout modele.

### 4. Docker Compose — stack de production

Produire un `docker-compose.yml` deployant l'ensemble en une commande :

| Service | Image | Port | Role |
|---|---|---|---|
| `db` | `postgres:16-alpine` | 5432 | Base PostgreSQL |
| `api` | `fastia-api:latest` (build local) | 8000 | API FastIA enrichie |
| `mlflow` | `ghcr.io/mlflow/mlflow:latest` | 5001 | MLflow Tracking + Registry |

Pour chaque service :
- Definir les **variables d'environnement** (via `.env.example` — ne PAS committer le `.env`)
- Configurer les **volumes** pour la persistance (donnees PostgreSQL, artefacts MLflow)
- Ajouter un **healthcheck** Docker natif (`HEALTHCHECK CMD curl -f http://localhost:8000/health`)
- Gerer l'**ordre de demarrage** (`depends_on` avec condition `service_healthy`)

Le `Dockerfile` de l'API doit :
- Partir de `python:3.11-slim`
- Copier et installer les dependances (requirements.txt)
- Copier le code source et les artefacts modeles
- Exposer le port 8000
- Lancer uvicorn avec les bons parametres (workers, host, port)

Ajouter un **`Makefile`** (ou scripts shell) avec les commandes essentielles :
- `make up` — lance la stack
- `make down` — arrete la stack
- `make logs` — affiche les logs
- `make test` — lance les tests dans un conteneur
- `make migrate` — applique les migrations

### 5. MLflow Model Registry — versionnement des modeles

Enregistrer les modeles dans le MLflow Model Registry :

**Script `scripts/register_models.py`** :
- Enregistrer le modele de classification (fine-tune M1) : nom `fastia-classification`, version 1
- Enregistrer le modele de langue retenu : nom `fastia-language`, version 1
- Enregistrer le modele de sentiment retenu : nom `fastia-sentiment`, version 1
- Pour chaque modele : logger les metriques du benchmark M4, les hyperparametres, un tag avec le hash du dataset d'entrainement
- Promouvoir en stage `Production`

**Chargement dynamique dans l'API** :
- L'API doit charger les modeles depuis le registre MLflow au demarrage (par nom + stage `Production`)
- Si le registre est inaccessible, fallback sur les artefacts locaux embarques dans l'image Docker
- Logger la version chargee de chaque modele au demarrage

### 6. Tests d'integration

Ecrire `tests/test_integration_stack.py` — tests bout en bout sur la stack deployee :

- La stack demarre sans erreur (`docker compose up -d` + attente healthcheck)
- `GET /health` retourne 200
- `POST /predict` avec un texte FR retourne une reponse enrichie complete (tous les champs)
- `POST /predict` avec un texte EN retourne `routed_priority: high_intl`
- `POST /predict` avec un texte contenant des homoglyphes retourne `sanitization.homoglyphs_replaced > 0`
- `POST /enrich` retourne langue + sentiment sans classification
- `GET /models` retourne les 3 modeles enregistres
- `GET /models/language/metrics` retourne les metriques du benchmark

---

## Livrables

| Livrable | Description |
|---|---|
| `src/pipeline/enrich_language.py` | Enrichissement langue production (cache, fallback, logging) |
| `src/pipeline/enrich_sentiment.py` | Enrichissement sentiment production |
| `src/pipeline/route.py` | Routage prioritaire |
| `src/api/endpoints.py` | Endpoints enrichis (`/predict`, `/enrich`, `/models`) |
| `docker-compose.yml` | Stack complete (PostgreSQL + API + MLflow) |
| `Dockerfile` | Image de l'API FastIA |
| `.env.example` | Variables d'environnement template |
| `Makefile` | Commandes de gestion de la stack |
| `scripts/register_models.py` | Enregistrement des modeles dans MLflow |
| `tests/test_integration_stack.py` | Tests bout en bout |
| `README.md` | Section "Module 5 — Brief 1" avec instructions de deploiement |

---

## Charge de travail estimee

6 heures

---

## Ressources

- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [Docker Compose — depends_on](https://docs.docker.com/compose/startup-order/)
- [Docker HEALTHCHECK](https://docs.docker.com/engine/reference/builder/#healthcheck)
- [FastAPI — Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Loguru](https://loguru.readthedocs.io/)
- [Pydantic v2 — BaseModel](https://docs.pydantic.dev/latest/)

---

## Bonus

- Ajouter **Adminer** (port 8080) au Docker Compose pour explorer la base via navigateur
- Implementer un **backfill CLI** (`python -m scripts.backfill --batch-size 100`) qui enrichit l'historique en base par lots
- Ajouter des **readiness et liveness probes** Kubernetes-ready sur l'API (endpoint `/ready` qui verifie la connexion DB + modeles charges)
- Implementer un **rate limiter** sur `/predict` (defense extraction de modele, cf. plan d'attenuation M4) via middleware FastAPI avec compteur in-memory ou Redis
