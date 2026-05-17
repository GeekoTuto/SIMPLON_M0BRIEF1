# Modèle proposé
from datetime import datetime
from pathlib import Path
from typing import Iterator
import json
import psycopg2
from psycopg2.extras import Json
from pydantic import BaseModel
from loguru import logger

from config import DB_DSN
from email_loader import _repair_common_mojibake
from lang_detect import detect_language

class RawDemande(BaseModel):
    canal: str = "email"
    external_id: str
    received_at: datetime
    sender: str | None
    subject: str | None
    body: str
    input_raw: str
    canal_metadata: dict

def load_web_jsonl(path: Path) -> Iterator[RawDemande]:
    with path.open() as f:
        for line in f:
            data = json.loads(line.strip())
            if not data:
                continue

            form = data.get("form", {})
            raw_body = form.get("message", "")
            body = _repair_common_mojibake(raw_body.strip())

            # ignore les soumissions vides ou trop courtes
            if len(body) < 10:
                continue

            yield RawDemande(
                canal="web",
                external_id=data.get("submission_id", ""),
                received_at=datetime.fromisoformat(data["submitted_at"].replace("Z", "+00:00")),
                sender=form.get("email"),
                subject=form.get("subject") or None,
                body=body,
                input_raw=raw_body,
                canal_metadata={
                    "user_agent": data.get("user_agent"),
                    "ip_country": data.get("ip_country"),
                    #"consent_marketing": form.get("consent_marketing"),
                },
            )

def insert_into_db(demandes: Iterator[RawDemande]) -> None:
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    try:
        for demande in demandes:
            logger.debug(f"Inserting into DB: {demande.external_id} - {demande.subject}")
            try:
                language = detect_language(demande.body)
                cur.execute(
                    """
                    INSERT INTO demandes
                        (canal, external_id, received_at, input_text, input_raw, categorie, priorite, dataset_version, langue, canal_metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canal, external_id) DO NOTHING
                    """,
                    (
                        demande.canal,
                        demande.external_id,
                        demande.received_at,
                        demande.body,
                        demande.input_raw,
                        "non_classifie",
                        "normale",
                        "web_jsonl_v1",
                        language,
                        Json({
                            "sender": demande.sender,
                            "subject": demande.subject,
                            **demande.canal_metadata,
                        }),
                    ),
                )
                if cur.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Error inserting {demande.external_id}: {e}")
                raise
        
        conn.commit()
        logger.info(f"Web insertions: {inserted} insérées, {skipped} doublons")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    for demande in load_web_jsonl(Path("data/raw/formulaires_web.json")):
        print(demande)
    insert_into_db(load_web_jsonl(Path("data/raw/formulaires_web.json")))


