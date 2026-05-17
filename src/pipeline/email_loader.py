from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from email.header import decode_header
from pathlib import Path
from typing import Iterator
import mailbox
import re

from bs4 import BeautifulSoup
from loguru import logger
from pydantic import BaseModel

try:
    from chardet import detect as chardet_detect  # pyright: ignore[reportMissingImports]
except ImportError:
    chardet_detect = None


# Modèle proposé
class RawDemande(BaseModel):
    canal: str = "email"
    external_id: str
    received_at: datetime
    sender: str | None
    subject: str | None
    body: str
    canal_metadata: dict


def decode_header_value(value: str | None) -> str | None:
    if not value:
        return None

    FALLBACK_ENCODINGS = {"unknown-8bit", "unknown", "x-unknown"}
    result = []

    for chunk, enc in decode_header(value):
        if not isinstance(chunk, bytes):
            result.append(chunk)
            continue

        if not enc or enc.lower() in FALLBACK_ENCODINGS:
            enc = "utf-8"

        result.append(chunk.decode(enc, errors="replace"))

    return "".join(result)


def parse_date(raw: str | None) -> datetime:
    """Parse une date email ; retourne now(UTC) en fallback."""
    if raw:
        try:
            return parsedate_to_datetime(raw)
        except Exception:
            pass
    logger.warning("Date invalide ou absente, fallback sur now(UTC)")
    return datetime.now(timezone.utc)


def _mojibake_score(text: str) -> int:
    """Heuristic score: lower is better for likely-correct French text."""
    bad_markers = ("�", "Ã", "Â")
    return sum(text.count(marker) for marker in bad_markers)


def _repair_common_mojibake(text: str) -> str:
    """Repair common UTF-8 decoded as Latin-1/CP1252 artifacts when safe."""
    if not text:
        return text

    if "Ã" not in text and "Â" not in text:
        return text

    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except Exception:
        return text

    return repaired if _mojibake_score(repaired) < _mojibake_score(text) else text


def decode_payload(payload: bytes, declared_charset: str | None) -> str:
    """Decode MIME payload using robust charset fallbacks for legacy emails."""
    candidates: list[str] = []

    if declared_charset:
        candidates.append(declared_charset)

    if chardet_detect is not None:
        detection = chardet_detect(payload) or {}
        detected_charset = detection.get("encoding")
        if detected_charset:
            candidates.append(detected_charset)

    candidates.extend(["utf-8", "cp1252", "latin-1"])

    # Keep order while removing duplicates.
    seen = set()
    ordered_candidates = []
    for encoding in candidates:
        normalized = encoding.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered_candidates.append(encoding)

    for encoding in ordered_candidates:
        try:
            decoded = payload.decode(encoding)
            return _repair_common_mojibake(decoded)
        except Exception:
            continue

    # Last resort: never fail extraction, keep a readable approximation.
    decoded = payload.decode("utf-8", errors="replace")
    return _repair_common_mojibake(decoded)

def _html_to_text(html: str) -> str:
    """Convertit une partie HTML en texte brut lisible via BeautifulSoup."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Supprimer les balises non-textuelles
    for tag in soup(["script", "style", "head", "meta", "link"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Réduire les lignes vides consécutives à une seule
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_body(message) -> str:
    """Extrait le texte brut d'un message MIME (plain > html > vide)."""
    plain, html = [], []

    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        charset = part.get_content_charset()
        text = decode_payload(payload, charset)

        match part.get_content_type():
            case "text/plain":
                plain.append(text)
            case "text/html":
                html.append(_html_to_text(text))

    return "\n".join(plain or html).strip()


def clean_body(text: str) -> str:
    """Supprime citations, signatures et blocs 'On … wrote:'."""
    # lignes de citation (>)
    lines = [l for l in text.splitlines() if not l.strip().startswith(">")]
    text = "\n".join(lines)
    # signature standard (-- )
    text = re.split(r"\n--\s*\n", text)[0]
    # bloc "On ... wrote:"
    text = re.split(r"\nOn .+? wrote:\s*$", text, flags=re.DOTALL)[0]
    return text.strip()


def load_mbox(path: Path) -> Iterator[RawDemande]:
    """Itère sur les messages d'un fichier mbox et yield un RawDemande par mail."""
    for message in mailbox.mbox(path):
        try:
            body = clean_body(extract_body(message))
            if len(body) < 10:
                logger.warning("Message ignoré : body trop court")
                continue

            yield RawDemande(
                external_id=decode_header_value(message.get("Message-ID")) or "",
                received_at=parse_date(message.get("Date")),
                sender=decode_header_value(message.get("From")),
                subject=decode_header_value(message.get("Subject")),
                body=body,
                canal_metadata={
                    "to":  decode_header_value(message.get("To")),
                    "cc":  decode_header_value(message.get("Cc")),
                    "bcc": decode_header_value(message.get("Bcc")),
                    "attachments": [
                        part.get_filename()
                        for part in message.walk()
                        if part.get_content_disposition() == "attachment"
                        and part.get_filename()
                    ],
                },
            )

        except Exception as e:
            logger.exception(f"Message ignoré : {e}")