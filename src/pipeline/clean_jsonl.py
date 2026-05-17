#Doublons	drop_duplicates()	#suppression des doublons exacts + quasi-doublons via hash normalisé
import re
import hashlib
import pandas as pd
import loguru
import fr_core_news_lg

def normalize_for_hash(text: str) -> str:
    """Normalize text for hashing by lowercasing and removing extra whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())

def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact and normalized duplicates from dataframe."""
    df = df.copy()
    df["input_hash"] = df["input"].map(lambda s: hashlib.md5(normalize_for_hash(s).encode()).hexdigest())
    
    # Identifier les doublons
    duplicates_mask = df.duplicated(subset=["input_hash"], keep="first")
    duplicate_indices = df[duplicates_mask].index.tolist()
    
    # Logger les lignes supprimées
    for idx in duplicate_indices:
        loguru.logger.info(f"SUPPRIMÉ (doublon) - Ligne {idx}: {df.iloc[idx]['input'][:100]}")
    
    df_cleaned = df[~duplicates_mask].reset_index(drop=True)
    df_cleaned = df_cleaned.drop(columns=["input_hash"])
    loguru.logger.info(f"Doublons supprimés: {len(duplicate_indices)} | Exemples restants: {len(df_cleaned)}")
    return df_cleaned

# PII patterns
PII_PATTERNS = {
    "email":     re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
    "telephone": re.compile(r"(?:(?:\+33|0)\s?[1-9])(?:[\s.-]?\d{2}){4}"),
    "url":       re.compile(r"https?://\S+"),
    "ip":        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

def analyze_spacy_entities(df: pd.DataFrame):
    spacy_counts = {"PER": 0, "ORG": 0, "GPE": 0}
    nlp = fr_core_news_lg.load()
    for doc in nlp.pipe(df["input"].tolist() + df["reponse_suggeree"].tolist(), batch_size=50):
        for ent in doc.ents:
            if ent.label_ in spacy_counts:
                spacy_counts[ent.label_] += 1
                if ent.label_ == "ORG":
                    print(f"ORg détectée : {ent.text} (label={ent.label_})")
                else:
                    print(f"Personne détectée : {ent.text} (label={ent.label_})")
            
    print("Entités nommées détectées par spaCy :")
    print(spacy_counts)

def contains_pii(text: str) -> bool:
    """Check if text contains any PII patterns."""
    for pattern in PII_PATTERNS.values():
        if pattern.search(text):
            return True
    return False

def remove_pii(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows containing PII from dataframe."""
    df = df.copy()
    pii_mask = df["input"].apply(contains_pii)

    for idx in df[pii_mask].index:
        loguru.logger.warning(f"SUPPRIMÉ (PII) - Ligne {idx}: {df.loc[idx, 'input'][:100]}")

    df_final = df[~pii_mask].reset_index(drop=True)
    loguru.logger.info(f"Lignes avec PII supprimées: {pii_mask.sum()} | Exemples restants: {len(df_final)}")
    return df_final

#Anonymise les données du dataframe sensible avec [nom], [email], [téléphone], etc. selon le type détecté et spacy pour les entités nommées (personnes, organisations, lieux)
def anonymize_pii_and_entities(df: pd.DataFrame) -> pd.DataFrame:
    """Anonymize PII and named entities in the dataframe."""
    nlp = fr_core_news_lg.load()
    
    def anonymize_text(text: str) -> str:
        # Anonymiser les PII
        for key, pattern in PII_PATTERNS.items():
            text = pattern.sub(f"[{key}]", text)
        
        # Anonymiser les entités nommées
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in {"PER", "ORG", "GPE"}:
                text = text.replace(ent.text, f"[{ent.label_}]")
        
        return text
    
    df_anonymized = df.copy()
    df_anonymized["input"] = df_anonymized["input"].apply(anonymize_text)
    df_anonymized["reponse_suggeree"] = df_anonymized["reponse_suggeree"].apply(anonymize_text)
    loguru.logger.info("Anonymisation des PII et entités nommées effectuée.")
    loguru.logger.info(f"Exemples anonymisés :\n{df_anonymized}")
    loguru.logger.info(f"Exemples originaux :\n{df}")
    return df_anonymized

