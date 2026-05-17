# Implementer la logique de routage prioritaire :
# langue != 'fr' → high_intl
# sentiment == 'negatif' et sentiment_score > 0.8 → high_negative
# sinon → normal
# Retourner un objet RoutingDecision (Pydantic) avec la priorite et la justification

from pydantic import BaseModel

class RoutingDecision(BaseModel):
    priority: str
    justification: str

def route_demande(langue: str, sentiment: str, sentiment_score: float) -> RoutingDecision:
    if langue != 'fr':
        return RoutingDecision(priority='high_intl', justification=f"Langue détectée : {langue}")
    if sentiment == 'negatif' and sentiment_score > 0.8:
        return RoutingDecision(priority='high_negative', justification=f"Sentiment négatif fort détecté (score={sentiment_score:.4f})")
    return RoutingDecision(priority='normal', justification="Aucune condition de routage prioritaire remplie")

