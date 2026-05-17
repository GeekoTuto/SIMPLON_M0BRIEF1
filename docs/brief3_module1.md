# Brief 3 — Conteneurisation et mise en production

## Contexte du projet

Votre modèle est entraîné, amélioré et exposé via une API. FastIA vient de signer de nouveaux contrats et doit pouvoir déployer cette solution rapidement sur différents environnements serveurs. Votre manager vous demande de **rendre l'application portable et prête pour la production** : le modèle et son API doivent pouvoir être déployés sur n'importe quelle machine en une seule commande, avec une traçabilité complète des appels et une validation du bon fonctionnement.

---

## Objectif principal

Conteneuriser le modèle fine-tuné et son API, mettre en place le logging et les tests fonctionnels, et produire une documentation de déploiement complète.

---

## Prérequis

- Brief 2 complété : modèle final sauvegardé dans `./model_final`, API FastAPI fonctionnelle dans `main.py`
- Docker installé sur votre machine

---

## Étapes du projet

### 1. Logging avec Loguru

En production, chaque appel à l'API doit être tracé pour permettre le débogage et le suivi des performances.

- Installer Loguru :
```bash
pip install loguru
```

- Journaliser dans `main.py` :
  - Chaque appel au endpoint `/predict` : texte reçu, catégorie prédite, priorité, temps de traitement en millisecondes
  - Chaque appel au endpoint `/health`
  - Les erreurs et exceptions

- Conserver les logs dans un fichier `logs/api.log`

- Format de log recommandé :
```
{time} | {level} | {endpoint} | input={input} | output={output} | duration={duration}ms
```

### 2. Tests fonctionnels avec Pytest

Avant de conteneuriser, il faut s'assurer que l'API fonctionne correctement. Un conteneur qui embarque une API défaillante est inutilisable.

- Installer Pytest :
```bash
pip install pytest httpx
```

- Ecrire des tests couvrant :
  - Le endpoint `/health` retourne un statut 200
  - Le endpoint `/predict` retourne un JSON valide avec les champs `categorie`, `priorite`, `reponse_suggeree`
  - La `categorie` retournée est bien dans la liste des catégories connues
  - La `priorite` retournée est `haute` ou `normale`
  - Le endpoint `/predict` retourne une erreur explicite sur une entrée vide
  - Le endpoint `/predict` retourne une erreur explicite sur une entrée non textuelle

- Lancer les tests et s'assurer qu'ils passent tous avant de passer à la conteneurisation :
```bash
pytest tests/ -v
```

- Versionner les tests dans un dossier `tests/` sur GitHub

### 3. Conteneurisation avec Docker

- Créer un fichier `requirements.txt` propre :
```bash
pip freeze > requirements.txt
```

- Créer un `Dockerfile` qui :
  - Part d'une image Python officielle légère
  - Installe toutes les dépendances
  - Copie le modèle fine-tuné et le code de l'API
  - Expose le bon port
  - Lance automatiquement l'API au démarrage

Structure minimale :
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- Créer un `.dockerignore` pour exclure les fichiers inutiles :
  - Environnements virtuels
  - Fichiers de logs
  - Checkpoints d'entraînement intermédiaires
  - Fichiers `.git`

- Construire l'image :
```bash
docker build -t fastia-model:v1 .
```

- Lancer le conteneur :
```bash
docker run -p 8000:8000 fastia-model:v1
```

- Vérifier que les endpoints répondent depuis l'extérieur du conteneur avec Postman ou curl

### 4. Vérification finale

Avant de livrer, effectuer les vérifications suivantes :

- L'image Docker se construit sans erreur
- L'API démarre correctement dans le conteneur
- Les endpoints `/predict` et `/health` répondent correctement depuis l'extérieur du conteneur
- Les logs sont bien générés dans `logs/api.log`
- Tous les tests Pytest passent

---

## Livrables

- **Dépôt GitHub** finalisé avec :
  - `main.py` avec logging intégré
  - `tests/` avec les tests Pytest
  - `Dockerfile` et `.dockerignore`
  - `requirements.txt`
  - Structure du dossier `logs/` (sans les fichiers de log)
- **README.md** finalisé documentant :
  - Architecture complète du projet
  - Procédure de lancement en local
  - Procédure de lancement avec Docker
  - Description des endpoints
  - Description du système de logs
  - Procédure d'exécution des tests
- **Rapport MLflow** : déjà produit en Brief 2, référencé dans le README

---

## Charge de travail estimée

3 à 5 heures

---

## Ressources

- [Documentation Loguru](https://loguru.readthedocs.io)
- [Documentation Pytest](https://docs.pytest.org)
- [Documentation Docker](https://docs.docker.com)

---

## Bonus

- Ajouter un `docker-compose.yml` pour lancer l'API et le serveur MLflow ensemble
- Ajouter un test vérifiant la cohérence entre catégorie et priorité dans la réponse
- Ajouter un endpoint `/metrics` retournant le nombre d'appels et le temps de traitement moyen depuis le démarrage
