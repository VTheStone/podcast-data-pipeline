"""
Integration test for src/processing/indexer.index_episode.
Uses a fake embedding model and fake ChromaDB collection — no real
model download, no GPU, no disk-backed ChromaDB needed, since both
are already injectable parameters in the real function signature.
"""

import numpy as np
from sqlalchemy.orm import Session

from src.ingestion.database import Episode, RAGChunk
from src.processing.indexer import index_episode


class FakeEmbeddingModel:
    """Stands in for sentence_transformers.SentenceTransformer."""

    def encode(self, texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True):
        return np.zeros((len(texts), 4))


class FakeCollection:
    """Stands in for a chromadb Collection — records calls instead of persisting."""

    def __init__(self):
        self.added_calls = []

    def add(self, ids, embeddings, documents, metadatas):
        self.added_calls.append(
            {"ids": ids, "embeddings": embeddings, "documents": documents, "metadatas": metadatas}
        )


def test_index_episode_updates_flag_and_calls_collection(engine):
    episode_id = "ep-index-fixture"

    with Session(engine) as session:
        session.add(Episode(id=episode_id, title="Index Fixture", chunked=True))
        session.flush()
        session.add(RAGChunk(episode_id=episode_id, chunk_index=0, text="First chunk of text.", token_count=4, start_time=0.0, end_time=5.0))
        session.add(RAGChunk(episode_id=episode_id, chunk_index=1, text="Second chunk of text.", token_count=4, start_time=5.0, end_time=10.0))
        session.commit()
        episode = session.get(Episode, episode_id)

    collection = FakeCollection()
    indexed_count = index_episode(engine, FakeEmbeddingModel(), collection, episode)

    assert indexed_count == 2
    assert collection.added_calls[0]["ids"] == [f"{episode_id}_0", f"{episode_id}_1"]

    with Session(engine) as session:
        updated_episode = session.get(Episode, episode_id)
        rag_chunks = session.query(RAGChunk).filter(
            RAGChunk.episode_id == episode_id
        ).order_by(RAGChunk.chunk_index).all()

    assert updated_episode.indexed is True
    assert rag_chunks[0].embedding_id == f"{episode_id}_0"
    assert rag_chunks[1].embedding_id == f"{episode_id}_1"


def test_index_episode_returns_zero_when_no_chunks(engine):
    episode_id = "ep-no-chunks"

    with Session(engine) as session:
        session.add(Episode(id=episode_id, title="No Chunks Episode", chunked=True))
        session.commit()
        episode = session.get(Episode, episode_id)

    indexed_count = index_episode(engine, FakeEmbeddingModel(), FakeCollection(), episode)

    assert indexed_count == 0