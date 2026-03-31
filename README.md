# SIMPLON_M0BRIEF1

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