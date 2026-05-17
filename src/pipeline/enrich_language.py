import fasttext
from loguru import logger

import config

ft_model = fasttext.load_model(config.FASTTEXT_MODEL_PATH.as_posix())

# Charger le modele retenu au benchmark M4 (langdetect, fasttext ou XLM-RoBERTa selon la recommandation)
# Implementer un cache par hash du body : si le texte a deja ete enrichi, retourner le resultat stocke sans re-inferer
# Gerer le fallback : si le modele echoue ou si la confiance est sous un seuil configurable (defaut 0.5), retourner langue=None sans bloquer la pipeline
# Logger chaque enrichissement avec Loguru (texte tronque, resultat, temps d'inference)



language_logger = logger.bind(channel="language")
def enrich_language(text: str) -> str:
    language_logger.info(f"Enrichissement langue : texte à analyser = '{text[:100]}'")
    try:
        predictions = ft_model.predict(text, k=1)
        language_code = predictions[0][0].replace("__label__", "")
        confidence = predictions[1][0]
        language_logger.info(f"Enrichissement langue : résultat = {language_code} (confiance={confidence:.4f})")
        if confidence < 0.5:
            language_logger.warning(f"Enrichissement langue : confiance faible ({confidence:.4f}), retour langue=None")
            return None
        return language_code
    except Exception as exc:
        language_logger.error(f"Enrichissement langue : erreur '{text[:100]}' : {exc}")
        return None

