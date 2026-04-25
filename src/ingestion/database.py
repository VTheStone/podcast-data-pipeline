"""
Database models and connection setup.
Uses SQLAlchemy with SQLite for local development.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Float,
)
from sqlalchemy.orm import declarative_base, relationship, Session
from loguru import logger

Base = declarative_base()


class Episode(Base):
    """Podcast episode metadata."""

    __tablename__ = "episodes"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    published_at = Column(String)
    duration_seconds = Column(Integer)
    description = Column(Text)
    audio_url = Column(String)
    image_url = Column(String)
    explicit = Column(String, default="no")

    # Pipeline control flags
    downloaded = Column(Boolean, default=False)
    transcribed = Column(Boolean, default=False)
    chunked = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    transcription = relationship("Transcription", back_populates="episode", uselist=False)
    chunks = relationship("Chunk", back_populates="episode")

    def __repr__(self):
        return f"<Episode {self.title}>"


class Transcription(Base):
    """Full transcription of a podcast episode with quality metrics."""

    __tablename__ = "transcriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=False)
    full_text = Column(Text)
    language = Column(String, default="pt")
    model_used = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    # Quality metrics
    total_segments = Column(Integer, nullable=True)
    total_chars = Column(Integer, nullable=True)
    estimated_words = Column(Integer, nullable=True)
    avg_logprob = Column(Float, nullable=True)        # confidence score
    repetition_rate = Column(Float, nullable=True)    # 1.0 = no repetition
    chars_per_minute = Column(Float, nullable=True)   # coverage metric
    language_confidence = Column(Float, nullable=True)
    hallucination_flag = Column(Boolean, default=False)  # True if repetition_rate < 0.5

    # Relationships
    episode = relationship("Episode", back_populates="transcription")
    chunks = relationship("Chunk", back_populates="transcription")

    def __repr__(self):
        return f"<Transcription episode_id={self.episode_id}>"


class Chunk(Base):
    """Text chunk from a transcription, used for RAG."""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=False)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False)
    chunk_index = Column(Integer)
    text = Column(Text)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    speaker = Column(String, nullable=True)
    embedding_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    episode = relationship("Episode", back_populates="chunks")
    transcription = relationship("Transcription", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk {self.chunk_index} episode_id={self.episode_id}>"


def get_engine(db_path: str = "data/metadata/podcast.db"):
    """
    Creates and returns the SQLAlchemy engine.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy engine instance.
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    logger.info(f"Database engine created at {db_path}")
    return engine


def init_db(db_path: str = "data/metadata/podcast.db"):
    """
    Initializes the database, creating all tables if they don't exist.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy engine instance.
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    logger.success("Database initialized successfully")
    return engine