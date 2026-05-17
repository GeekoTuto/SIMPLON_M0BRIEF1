#chainer : cleaning → sanitize (M4) → enrich_language → enrich_sentiment → route → stockage
#L'enrichissement doit etre idempotent : relancer la pipeline sur une ligne deja enrichie ne doit pas la re-traiter (sauf flag --force)

from loguru import logger

from .email_loader import RawDemande
from .web_loader import load_web_jsonl, insert_into_db
from .enrich_language import enrich_language
from .enrich_sentiment import enrich_sentiment
from .route import route_demande

def run_pipeline(web_jsonl_path: str) -> None:
    demandes = load_web_jsonl(web_jsonl_path)
    for demande in demandes:
        langue = enrich_language(demande.body)
        sentiment, sentiment_score = enrich_sentiment(demande.body)
        routing_decision = route_demande(langue, sentiment, sentiment_score)
        # Ici on pourrait ajouter un champ dans la DB pour stocker la decision de routage et la justification
        logger.info(f"Demande {demande.external_id} : routage={routing_decision.priority} (justification={routing_decision.justification})")
    insert_into_db(demandes)

