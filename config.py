from pathlib import Path
import os

# Repertoire racine du projet (portable local + Docker)
# - Par defaut: dossier parent de ce fichier (ex: /app en conteneur)
# - Override possible via FASTIA_PROJECT_ROOT
PROJECT_ROOT = Path(
    os.environ.get("FASTIA_PROJECT_ROOT", Path(__file__).resolve().parent)
).resolve()
DATA_EVAL = PROJECT_ROOT / "data" / "eval"
DATA_ADV = PROJECT_ROOT / "data" / "adversarial"
SENTIMENT_FILE = DATA_EVAL / "sentiment_eval_50 copy.jsonl"

# Override possible via FASTIA_FASTTEXT_MODEL_PATH
FASTTEXT_MODEL_PATH = Path(
    os.environ.get("FASTIA_FASTTEXT_MODEL_PATH", PROJECT_ROOT / "lid.176.bin")
).resolve()
# BDD
DB_DSN = os.environ.get(
    "FASTIA_DB_DSN",
    "postgresql://postgres:P%40stgreSql@localhost:5432/fastia",
)