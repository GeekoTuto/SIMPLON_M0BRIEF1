# Candidat 2 : bert-multilingual-sentiment

from transformers import pipeline

sentiment_bert_multi = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
    device=-1,
)

BERT_MULTI_MAPPING = {
    "1 star": "negatif",
    "2 stars": "negatif",
    "3 stars": "neutre",
    "4 stars": "positif",
    "5 stars": "positif",
}


def enrich_sentiment(text: str) -> dict:
    result = sentiment_bert_multi(text[:512])[0]
    label = result["label"].lower()
    sentiment = BERT_MULTI_MAPPING.get(label, "neutre")
    return {
        "sentiment": sentiment,
        "sentiment_score": float(result["score"]),
    }