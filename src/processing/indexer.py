"""
Vector indexing pipeline for Phase 5.
Generates embeddings for RAG chunks and stores them in ChromaDB
with rich metadata for filtered retrieval.
"""

from datetime import datetime
import json
import torch
from loguru import logger
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
import chromadb

from src.ingestion.config import (
    EMBEDDING_MODEL,
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    DISTANCE_METRIC,
)
from src.ingestion.database import (
    Episode,
    RAGChunk,
    get_engine,
)


def get_device() -> str:
    """Returns best available device for embedding generation."""
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_embedding_model() -> SentenceTransformer:
    """Loads the embedding model on the best available device."""
    device = get_device()
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL} on {device}")
    model = SentenceTransformer(EMBEDDING_MODEL, device=device)
    logger.success("Embedding model loaded successfully")
    return model


def get_chroma_collection():
    """
    Creates or retrieves the ChromaDB collection.

    Returns:
        ChromaDB collection instance.
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": DISTANCE_METRIC},
    )
    logger.info(f"ChromaDB collection ready: {CHROMA_COLLECTION_NAME}")
    return collection


def build_chunk_metadata(chunk: RAGChunk, episode: Episode) -> dict:
    """
    Builds metadata dictionary for a chunk.
    All values must be strings, ints, floats or bools (ChromaDB constraint).

    Args:
        chunk: RAGChunk database instance.
        episode: Episode database instance.

    Returns:
        Metadata dictionary.
    """
    speakers_list = json.loads(chunk.speakers) if chunk.speakers else []
    return {
        "episode_id": episode.id,
        "episode_title": episode.title,
        "published_at": episode.published_at or "",
        "duration_seconds": episode.duration_seconds or 0,
        "chunk_index": chunk.chunk_index,
        "start_time": chunk.start_time,
        "end_time": chunk.end_time,
        "speakers": ",".join(speakers_list) if speakers_list else "",
        "token_count": chunk.token_count or 0,
    }


def index_episode(
    engine,
    model: SentenceTransformer,
    collection,
    episode: Episode,
    batch_size: int = 32,
) -> int:
    """
    Generates embeddings and indexes all chunks of an episode.

    Args:
        engine: SQLAlchemy engine.
        model: Loaded embedding model.
        collection: ChromaDB collection.
        episode: Episode to index.
        batch_size: Number of chunks per embedding batch.

    Returns:
        Number of chunks indexed.
    """
    with Session(engine) as session:
        chunks = session.query(RAGChunk).filter(
            RAGChunk.episode_id == episode.id
        ).order_by(RAGChunk.chunk_index).all()

        if not chunks:
            logger.warning(f"No chunks found for: {episode.title[:60]}")
            return 0

        # Prepare data for batch embedding
        texts = [c.text for c in chunks]
        ids = [f"{episode.id}_{c.chunk_index}" for c in chunks]
        metadatas = [build_chunk_metadata(c, episode) for c in chunks]

        # Generate embeddings in batches (more efficient on GPU)
        logger.info(f"Generating {len(texts)} embeddings...")
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        # Add to ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
        )

        # Update embedding_id in SQL for traceability
        for chunk, chunk_id in zip(chunks, ids):
            chunk.embedding_id = chunk_id

        # Mark episode as indexed
        ep = session.get(Episode, episode.id)
        ep.indexed = True

        session.commit()

    return len(chunks)


def run(max_episodes: int = None):
    """
    Main entry point for the indexing pipeline.

    Args:
        max_episodes: Maximum episodes to index (None = all).
    """
    engine = get_engine()

    with Session(engine) as session:
        query = session.query(Episode).filter(
            Episode.chunked == True,
            Episode.indexed == False,
        )

        if max_episodes:
            query = query.limit(max_episodes)

        episodes = query.all()

    total = len(episodes)
    logger.info(f"Episodes pending indexing: {total}")

    if total == 0:
        logger.success("All chunked episodes already indexed")
        return

    # Load model and ChromaDB once
    model = load_embedding_model()
    collection = get_chroma_collection()

    success_count = 0
    failed_count = 0
    failed_episodes = []
    total_chunks_indexed = 0

    for i, episode in enumerate(episodes, 1):
        logger.info(f"[{i}/{total}] Indexing: {episode.title[:60]}")

        try:
            chunks_count = index_episode(engine, model, collection, episode)
            success_count += 1
            total_chunks_indexed += chunks_count
            logger.success(f"Indexed {chunks_count} chunks")

        except Exception as e:
            logger.error(f"Failed to index {episode.title[:60]}: {e}")
            failed_count += 1
            failed_episodes.append(episode.title)

    # Final report
    logger.info("=== Indexing Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully indexed: {success_count}")
    logger.info(f"Total chunks indexed: {total_chunks_indexed}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()