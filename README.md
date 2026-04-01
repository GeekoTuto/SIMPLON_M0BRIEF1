# SIMPLON_M0BRIEF1

## Fonctionnalités
- Dans l'onglet app : Application d'Analyse de sentiment. L'utilisateur entre un texte en anglais et l'application analysera quel sentiment s'en dégage.

- Dans l'onglet Segmentation : L'application peut charger une image afin de l'analyser et de créer plusieurs segments qui seront analysés 1 par 1. Une description globale sera faites par la suite en fonction de ces différents segments 

## Prerequis

- Python

## Installation

Dans le terminal ou dans Powershell, depuis le dossier du projet :

```powershell
python -m venv .venv
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Lancer l'API

L'application Streamlit appelle l'API sur le port `8001`.

```powershell
python -m uvicorn api:app --port 8001 --reload
```

ouvrir `http://127.0.0.1:8001/` 

## Lancer l'application StreamLit

```powershell
python -m streamlit run app.py
```

L'URL concernée par la requête post du Front :

```text
http://127.0.0.1:8001/analyse_sentiment/
```

## Architecture

### Structure globale

Architecture **API + Client** :

```
Client Streamlit (app.py)
        ↓ (requête POST)
    API FastAPI (api.py)
        ↓ (traitement)
    Moteur VADER
        ↓ (scores)
    Réponse JSON
```

### Composants

#### 1. **API FastAPI** (`api.py`)
L'API REST qui traite l'analyse de sentiment :
- **Port** : 8001
- **GET** `/` : Vérification que l'API est fonctionnelle
- **POST** `/analyse_sentiment/` : Analyse le texte fourni
  - Entrée : texte JSON (`{"text": "..."}`).
  - Sortie : scores de sentiment sous forme JSON
    - `neg` : score de négativité
    - `neu` : score de neutralité
    - `pos` : score de positivité
    - `compound` : score global
- **Analyse** : VADER 

#### 2. **Interface Streamlit** (`app.py`)
Application web interactive pour l'utilisateur :
- Champ de saisie : l'utilisateur entre un texte en **anglais**
- Bouton "Analyser" : envoie une requête POST à l'API
- Affichage des résultats :
  - Interprétation globale du sentiment (Positif 😀 / Neutre 😐 / Négatif 🙁)

#### 3. **Logging**
Système de log :
- `logs/sentiment_api.log` : logs de l'API 
- `logs/sentiment_streamlit.log` : logs client

## Tests unitaires

```powershell
python -m pytest -v
```

```python
Exemples de tests réussis
tests/test_api.py::test_home PASSED                                                                                            [ 33%] 
tests/test_api.py::test_analyse_sentiment_positive PASSED                                                                      [ 66%] 
tests/test_api.py::test_analyse_sentiment_negative PASSED    
```