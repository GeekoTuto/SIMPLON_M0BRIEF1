import nltk
nltk.download('vader_lexicon', quiet=True)

from fastapi import FastAPI
from loguru import logger
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from controllers.image_controller import router as image_router
from controllers.sentiment_controller import router as sentiment_router

os.makedirs("logs", exist_ok=True)
logger.remove()
logger.add(
	"logs/sentiment_api.log",
	rotation="500 MB",
	level="INFO",
	filter=lambda record: record["extra"].get("channel") == "sentiment",
)
logger.add(
	"logs/analyse_image.log",
	rotation="500 MB",
	level="INFO",
	filter=lambda record: record["extra"].get("channel") == "image",
)

##model_path = "./model_run3"
##tokenizer = AutoTokenizer.from_pretrained(model_path)
##model = AutoModelForSequenceClassification.from_pretrained(model_path)

app = FastAPI()
app.include_router(sentiment_router)
app.include_router(image_router)