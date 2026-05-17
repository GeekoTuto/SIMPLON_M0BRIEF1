# Threat Model — Pipeline LOCAL

**Périmètre :** Pipeline d'ingestion avec 3 sources (email, web, chat) avec détection de langue (fasttext) et sentiment (bert-multilingual), exposition via API.  
**Référence :** [MITRE ATLAS](https://atlas.mitre.org/) · [NIST AI 100-2 (Adversarial Machine Learning)](https://airc.nist.gov/Publications/1)

---

## Résumé

FastIA utilise trois canaux effectue différentes opérations (détection de langue, analyse de sentiment, routage prioritaire). L'Api est donc exposée aux menace

Le modèle de menace couvre 4 familles issues des docs en référence

---

## Familles de menaces

### 1. Évasion (Adversarial Evasion)

**Description**  
L'évasion consiste à manipuler une entrée pour tromper le modèle sans en modifier les paramètres. L'attaquant exploite les failles lors de l'apprentissage du modèle.

**Vecteur d'attaque concret**  
Un expéditeur remplace des lettres normales par des **homoglyphes** dans le mail ou autre document ou texte en entrée. Cela pass inaperçu et fausse la détection de langue ou la classification prévue. 

**Impact sur FastIA**

| Dimension CIA | Effet |
|---|---|
| Confidentialité | Faible |
| Intégrité | **Élevé** — langue incorrecte, sentiment prédiction ... |
| Disponibilité | Faible — pas de pb pour le service. |

**Détectabilité :** dur à détecter.

**Tests pratiques :** test adversarial avec des homoglyphes

**Contre-mesures :**  

Normalisation Unicode NFKC avant tout traitement

---

### 2. Empoisonnement de données (Data Poisoning)

**Description**  
Injection de données malveillantes ou fausses dans le jeu d'entraînement. Cible l'apprentissag de données.

**Vecteur d'attaque concret**  
Ligne fausse avec des données incohérentes, fausse l'apprentissage et entraine des biais.

**Impact sur FastIA**

| Dimension CIA | Effet |
|---|---|
| Confidentialité | Faible. |
| Intégrité | **Élevé** — score erroné et données non fiable. |
| Disponibilité | Moyen — service ok mais qualité dégradée. |

**Détectabilité :** controler l'acces au fichier

**Tests pratiques :** Simulation d'un dégradation de données.

**Contre-mesures**  
contrôle d'accès ; validation, versionning

---

### 3. Injection de prompt (Prompt Injection)

> **Références :** MITRE ATLAS — AML.T0051 · NIST AI 100-2 — Section 2.5 (Prompt Injection)

**Description**  
Insértion en entrée d'instructions interprétées comme des directives par un LLM. 

**Vecteur d'attaque concret**  
une personne écrit une demande qui sera lu comme une instructions par le LLM entrainant une exécution malveillante

**Impact sur FastIA**

| Dimension CIA | Effet |
|---|---|
| Confidentialité | **Élevé** — instructions dangereuses, prompt compromis. |
| Intégrité | **Élevé** — manipulation des décisions. |
| Disponibilité | Faible — service OK. |

**Détectabilité :** Difficile — des patterns existens mais difficile à voir

**Tests pratiques (étape 5) :** tester une injection et comment la voir

**Contre-mesures**  
mettre en place des regex et pattern de détection
---

### 4. Extraction de modèle (Model Extraction)

**Description**  
Interroger une api afin de lui sous tirer des informations afin de la reconstruire ou d'en comprendre le comportement et l'entrainement précédemment effectué

**Vecteur d'attaque concret**  
envoie des requetes avec des demandes que l'utisateur récupère

**Impact sur FastIA**

| Dimension CIA | Effet |
|---|---|
| Confidentialité | **Élevé** — compromise, plus de confidentialité |
| Intégrité | Moyen — le modèle extrait peut servir pour la création d'attaque. |
| Disponibilité | Moyen — saturation du modèle si trop de requetes. |

**Détectabilité :** vérifier si une ip en particulier envoie trop de requetes, monitorer le nombre de requetes et détecter les pics anormaux

**Tests pratiques :** Simuler des requetes sur l'api

**Contre-mesures**  
authentification obligatoire, monitoring des appels

---

## Matrice de risque résumée

| Famille | Probabilité | Impact CIA | Criticité | Détectabilité | Priorité |
|---|---|---|---|---|---|
| Évasion | Élevée | Intégrité | **Critique** | Difficile | Immédiat |
| Injection de prompt | Moyenne | Confidentialité + Intégrité | **Élevé** | Difficile | Court terme |
| Extraction de modèle | Moyenne | Confidentialité | **Moyen** | Difficile | Court terme |
| Empoisonnement | Faible | Intégrité | **Moyen** | Non détecté | Moyen terme |