import nltk
nltk.download('vader_lexicon', quiet=True)

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from nltk.sentiment import SentimentIntensityAnalyzer
from loguru import logger
import os

from transformers.tokenization_utils_base import TextInput

os.makedirs("logs", exist_ok=True)
logger.add("logs/sentiment_api.log", rotation="500 MB", level="INFO")

app = FastAPI()
sia = SentimentIntensityAnalyzer()

class TextInput(BaseModel):
    text: str

@app.get("/")
def home():
    logger.info("Test api")
    return {"message": "API running"}


@app.post("/analyse_sentiment/")
def analyse_sentiment(payload: TextInput):
    logger.info(f"Requête : texte='{payload.text}'")
    try:
        scores = sia.polarity_scores(payload.text)
        result = {
            "neg": scores["neg"],
            "neu": scores["neu"],
            "pos": scores["pos"],
            "compound": scores["compound"],
        }
        logger.debug(f"Résultat : {result}")
        return result
    except Exception as e:
        logger.error(f"Erreur '{payload.text}' : {e}")
        return JSONResponse(status_code=500, content={"detail": "Erreur"})
