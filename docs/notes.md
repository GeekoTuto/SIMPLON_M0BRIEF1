# Notes

## Modèle de langue choisi

- Je partira sur fasttext car il est plus rapide avec une latence de 0.02ms et il a une accuracy de 1
- Ce qui en fait donc un modèle précis dans la détection de langue et très rapide
- La ram utilisée est quasi nulle

## Modèle de sentiment choisi

- le 2ème bert-multilingual-sentiment meilleur accuracy et multilingue

### Adverserial

- Le modèle s'est trompé sur les homoglyph sauf pour 1 ex (fasttext), il se trompe aussi sur les edges cases mais aucune erreur dans fasttext contrairement à langdetect

#### Langues

```json
{'langdetect': {'accuracy': 9.8, 'f1_macro': 9.855908986343769, 'robustesse': 3.333333333333333, 'latence': 0.0, 'memoire': 0.0, 'integration': 10}}

{'fasttext': {'accuracy': 10.0, 'f1_macro': 10.0, 'robustesse': 5.0, 'latence': 10.0, 'memoire': 10.0, 'integration': 9}}
```
```
langdetect: 6.08/10
fasttext: 8.95/10
```

- **fast_text** => retenu


#### Sentiments

```json
Scores sentiment : {'distilcamembert': {'accuracy': 6.6000000000000005, 'f1_macro': 5.366848205557883, 'robustesse': 5.0, 'latence': 10.0, 'memoire': 10.0, 'integration': 7}, 

'bert-multilingual': {'accuracy': 7.4, 'f1_macro': 7.106806564433684, 'robustesse': 6.333333333333333, 'latence': 0.0, 'memoire': 0.0, 'integration': 6}}
```

- Si multilingue bert-multilingual mais plus lourd et moins bon en français
- Si que du français on va plutôt prendre camembert qui est plus léger et adapter au français
