# Brief 2 — Itération et amélioration du modèle

## Contexte du projet

Votre premier modèle est entraîné et évalué. Votre diagnostic du Brief 1 a mis en évidence des axes d'amélioration. Votre manager vous demande maintenant de **mettre en oeuvre les actions correctives identifiées**, de réentraîner le modèle et de comparer les résultats avec le run initial.

C'est le coeur du travail d'un développeur IA : l'entraînement n'est jamais une étape unique. C'est un cycle itératif — évaluer, comprendre, corriger, réentraîner.

---

## Objectif principal

Mettre en oeuvre au moins une action corrective issue du diagnostic du Brief 1, réentraîner le modèle, comparer les deux runs dans MLflow et exposer le meilleur modèle via une API FastAPI.

---

## Prérequis

- Brief 1 complété
- Diagnostic écrit produit avec au moins une action corrective identifiée

---

## Étapes du projet

### 1. Mise en oeuvre des actions correctives

En fonction de votre diagnostic, appliquez **au moins une** des actions suivantes :

**Option A — Compléter le dataset**

Si votre diagnostic a révélé que certaines catégories sont mal classifiées, le dataset est probablement insuffisant sur ces cas.

- Identifier les catégories ou types de demandes sous-représentés ou mal gérés
- Ajouter entre 20 et 50 nouveaux exemples ciblés sur ces cas
- Respecter le format JSON du dataset existant
- Vérifier que la distribution globale reste équilibrée après ajout
- Versionner le nouveau dataset sur GitHub

**Option B — Ajuster les hyperparamètres**

Si votre diagnostic a révélé un sous-apprentissage ou un sur-apprentissage :

- Sous-apprentissage (loss élevée, prédictions incohérentes) : augmenter le learning rate, augmenter le nombre d'époques
- Sur-apprentissage (train loss basse, eval loss haute) : réduire le learning rate, réduire le nombre d'époques, augmenter le dropout LoRA
- Documenter votre raisonnement : pourquoi ces valeurs ?

**Option C — Les deux**

Si votre diagnostic le justifie, combinez les deux actions. Dans ce cas, versionner le dataset enrichi séparément avant de lancer l'entraînement.

### 2. Réentraînement — Run 2

- Relancer l'entraînement avec les corrections appliquées
- Tracker le run dans MLflow avec les mêmes métriques que le Run 1 :
  - Paramètres : learning rate, batch size, nombre d'époques, taille du dataset
  - Métriques : loss d'entraînement, loss de validation par époque

### 3. Comparaison Run 1 vs Run 2

Dans MLflow, comparer les deux runs :

- Les courbes de loss ont-elles évolué dans le sens attendu ?
- L'écart train loss / eval loss s'est-il réduit ?
- Les prédictions qualitatives se sont-elles améliorées sur les cas problématiques identifiés ?

Produire un tableau comparatif :

| Métrique | Run 1 | Run 2 |
|----------|-------|-------|
| Train loss finale | | |
| Eval loss finale | | |
| Dataset size | | |
| Learning rate | | |
| Epochs | | |

### 4. Choix du meilleur modèle

- Sur la base de la comparaison, choisir le meilleur run
- Justifier ce choix par écrit : la loss seule ne suffit pas, la qualité des prédictions compte
- Sauvegarder le meilleur modèle dans `./model_final`

### 5. Exposition via FastAPI

Développer l'API FastAPI dans un fichier `main.py` :

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/predict` | POST | Reçoit une demande texte, retourne le JSON structuré |
| `/health` | GET | Vérifie l'état de l'API et du modèle |

Le endpoint `/predict` accepte :
```json
{ "text": "texte de la demande client" }
```

Et retourne :
```json
{
  "categorie": "...",
  "priorite": "...",
  "reponse_suggeree": "..."
}
```

- Valider les données d'entrée avec Pydantic
- Tester les endpoints avec Postman ou curl
- Versionner `main.py` sur GitHub

---

## Livrables

- **Dépôt GitHub** mis à jour avec :
  - Le dataset enrichi si Option A ou C appliquée
  - Le notebook ou script de réentraînement
  - Le fichier `main.py` de l'API FastAPI
- **README.md** complété avec :
  - Description de l'action corrective appliquée et sa justification
  - Tableau comparatif Run 1 vs Run 2
  - Justification du choix du meilleur modèle
  - Procédure de lancement de l'API
- **Rapport MLflow exporté** : comparaison des deux runs avec courbes et métriques

---

## Charge de travail estimée

4 à 6 heures

---

## Ressources

- [Documentation PEFT](https://huggingface.co/docs/peft)
- [Documentation MLflow](https://mlflow.org/docs/latest/index.html)
- [Documentation FastAPI](https://fastapi.tiangolo.com)
- [Documentation Pydantic](https://docs.pydantic.dev)

---

## Bonus

- Tester le modèle sur des demandes rédigées volontairement de façon ambiguë ou avec des fautes
- Ajouter un endpoint `/categories` retournant la liste des catégories supportées
