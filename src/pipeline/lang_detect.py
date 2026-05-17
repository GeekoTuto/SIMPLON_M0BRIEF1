from __future__ import annotations

import re

from langdetect import DetectorFactory, LangDetectException, detect_langs


# Make detection deterministic across runs.
DetectorFactory.seed = 0


def detect_language(text: str | None, min_chars: int = 20, min_confidence: float = 0.70) -> str:
    """Return ISO language code (e.g. fr, en) or 'und' when uncertain."""
    if not text:
        return "und"

    compact = re.sub(r"\s+", " ", text).strip()
    alpha_count = sum(1 for char in compact if char.isalpha())
    if len(compact) < min_chars or alpha_count < 8:
        return "und"

    try:
        guesses = detect_langs(compact)
    except LangDetectException:
        return "und"
    except Exception:
        return "und"

    if not guesses:
        return "und"

    best_guess = guesses[0]
    if best_guess.prob < min_confidence:
        return "und"
    return best_guess.lang
