from sqlalchemy import Column, String, Float, TIMESTAMP, Integer, Text, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Demande(Base):
    """Model for demandes table"""
    __tablename__ = "demandes"

    id = Column(Integer, primary_key=True)
    canal = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=True)
    received_at = Column(TIMESTAMP(timezone=True), nullable=True)
    inserted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    canal_metadata = Column(JSON, nullable=True)
    input_text = Column(Text, nullable=False)
    input_raw = Column(Text, nullable=True)
    categorie = Column(String, nullable=False)
    priorite = Column(String, nullable=False)
    reponse_suggeree = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    langue = Column(String(10), nullable=True, default='fr')
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))
    dataset_version = Column(String(20), nullable=False)
    dedup_status = Column(String, nullable=False, default='unique')
    
    # Enrichment fields (added by migration)
    langue_confidence = Column(Float, nullable=True)
    sentiment = Column(String(10), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    enriched_at = Column(TIMESTAMP(timezone=True), nullable=True)
    routed_priority = Column(String(20), nullable=True)
