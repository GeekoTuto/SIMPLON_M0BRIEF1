import json
import uuid
import numpy as np
import pandas as pd

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger
from nltk.sentiment import SentimentIntensityAnalyzer
from pydantic import BaseModel
from sympy import false
from transformers import pipeline as hf_pipeline
from src.benchmark.sentiment_benchmark import benchmark_sentiment_model
from config import DATA_EVAL, SENTIMENT_FILE
from src.benchmark.fasttext_benchmark import benchmark_fasttext
from src.pipeline.enrich_language import enrich_language
from src.pipeline.enrich_sentiment import BERT_MULTI_MAPPING, enrich_sentiment
from src.pipeline.route import route_demande

router = APIRouter()
sia = SentimentIntensityAnalyzer()
sentiment_logger = logger.bind(channel="sentiment")


class TextInput(BaseModel):
    text: str


@router.get("/")
def home():
    sentiment_logger.info("Test api")
    return {"message": "L'API marche correctement"}

@router.post("/analyse_sentiment/")
def analyse_sentiment(text: TextInput):
    request_id = str(uuid.uuid4())
    sentiment_logger.info(f"Requête {request_id} : texte à analyser = '{text.text}'")
    try:
        scores = sia.polarity_scores(text.text)
        result = {
            "neg": scores["neg"],
            "neu": scores["neu"],
            "pos": scores["pos"],
            "compound": scores["compound"],
        }
        sentiment_logger.info(f"Requête {request_id} : Résultat = {result}")
        return result
    except Exception as exc:
        sentiment_logger.error(f"Requête {request_id} : Erreur '{text.text}' : {exc}")
        return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})

#Entrée Json ou JsonL avec un champ "text" pour le texte à analyser
#Sortie Json avec les champs : categorie, priorite, reponse_suggeree, langue, langue_confidence, sentiment, sentiment_score, routed_priority, sanitization (injection_suspected, homoglyphs_replaced)   
@router.post("/predict/")
def predict (text: TextInput):
 

 return {
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

# POST /predict avec un texte FR retourne une reponse enrichie complete (tous les champs)
# POST /predict avec un texte EN retourne routed_priority: high_intl
# POST /predict avec un texte contenant des homoglyphes retourne sanitization.homoglyphs_replaced > 0
# POST /enrich retourne langue + sentiment sans classification
# GET /models retourne les 3 modeles enregistres
# GET /models/language/metrics retourne les metriques du benchmark

@router.get("/models")
def get_models():
    return {
        "language_model": "fasttext",
        "sentiment_model": "bert-multilingual-sentiment",
        "routing_model": "rule-based"
    }

@router.get("/models/language/metrics")
def get_language_metrics():

    with open(DATA_EVAL / "langue_eval_200.jsonl", "r", encoding="utf-8") as f:
        langue_data = [json.loads(line) for line in f if line.strip()]

    df_langue = pd.DataFrame(langue_data)
    
    results_fasttext = benchmark_fasttext(
        df_langue["text"].tolist(), df_langue["lang"].tolist()
    )

    return {
        "model": "fasttext",
        "accuracy": results_fasttext["accuracy"],
        "f1_score": results_fasttext["f1_score"],
        "confusion_matrix": results_fasttext["confusion_matrix"].tolist(),
        "temps_moyen": f"Temps moyen : {np.mean(results_fasttext['times_ms'])} ms",
        "ram_peak_mb": results_fasttext["ram_peak_mb"],
        "gpu_peak_mb": results_fasttext["gpu_peak_mb"]
    }

@router.get("/models/sentiment/metrics")
def get_sentiment_metrics():

    if SENTIMENT_FILE.exists():
        with open(SENTIMENT_FILE, "r", encoding="utf-8") as f:
            sentiment_data = [json.loads(line) for line in f if line.strip()]
        df_sentiment = pd.DataFrame(sentiment_data)
        print(f"Lignes chargées : {len(df_sentiment)}")
        print(df_sentiment["sentiment"].value_counts())
    else:
        print("⚠ Fichier sentiment_eval_50.jsonl non trouvé.")
        print("  → Compléter l'étape 2 d'abord (annotation manuelle).")
        df_sentiment = None

    sentiment_bert_multi = hf_pipeline(
        "sentiment-analysis",
        model="nlptown/bert-base-multilingual-uncased-sentiment",
        device=-1,
    )

    if df_sentiment is not None:
        results_bert_multi = benchmark_sentiment_model(
            sentiment_bert_multi,
            BERT_MULTI_MAPPING,
            df_sentiment["text"].tolist(),
            df_sentiment["sentiment"].tolist(),
            "bert-multilingual",
        )

    return {
        "model": "bert-multilingual-sentiment",
        "accuracy": results_bert_multi["accuracy"] if df_sentiment is not None else None,
        "f1_score": results_bert_multi["f1_macro"] if df_sentiment is not None else None,
        "confusion_matrix": results_bert_multi["confusion_matrix"].tolist() if df_sentiment is not None else None,
        "temps_moyen": f"Temps moyen : {np.mean(results_bert_multi['times_ms'])} ms" if df_sentiment is not None else None,
        "ram_peak_mb": results_bert_multi["ram_peak_mb"] if df_sentiment is not None else None,
        "gpu_peak_mb": results_bert_multi["gpu_peak_mb"] if df_sentiment is not None else None
    }

@router.post("/enrich")
def enrich(text: TextInput):
    language = enrich_language(text.text)
    sentiment_result = enrich_sentiment(text.text)
    routing_decision = route_demande(language, sentiment_result["sentiment"], sentiment_result["sentiment_score"])
    return {
        "langue": language,
        "sentiment": sentiment_result["sentiment"],
        "sentiment_score": sentiment_result["sentiment_score"],
        "routed_priority": routing_decision.priority,
        "routing_justification": routing_decision.justification
    }
