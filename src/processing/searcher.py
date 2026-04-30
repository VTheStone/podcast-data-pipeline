"""
Semantic search interface for the indexed podcast chunks.
Provides a clean API for querying the vector database with optional filters.
"""

import torch
from loguru import logger
from sentence_transformers import SentenceTransformer
import chromadb

from src.ingestion.config import (
    EMBEDDING_MODEL,
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
)


class SemanticSearcher:
    """
    Semantic search interface for podcast chunks.
    Loads the embedding model and ChromaDB collection once for reuse.
    """

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading embedding model on {self.device}")
        self.model = SentenceTransformer(EMBEDDING_MODEL, device=self.device)

        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = client.get_collection(CHROMA_COLLECTION_NAME)
        logger.info(f"Connected to collection: {CHROMA_COLLECTION_NAME}")
        logger.info(f"Total documents available: {self.collection.count()}")

    def search(
        self,
        query: str,
        n_results: int = 5,
        episode_id: str = None,
        speaker: str = None,
    ) -> list[dict]:
        """
        Searches for chunks semantically similar to the query.

        Args:
            query: Natural language query.
            n_results: Number of results to return.
            episode_id: Optional filter by specific episode.
            speaker: Optional filter by speaker label.

        Returns:
            List of result dictionaries with text, metadata and similarity score.
        """
        # Generate query embedding
        query_embedding = self.model.encode(query, convert_to_numpy=True)

        # Build filter
        where_filter = {}
        if episode_id:
            where_filter["episode_id"] = episode_id
        if speaker:
            where_filter["speakers"] = {"$contains": speaker}

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where_filter if where_filter else None,
        )

        # Format results
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "similarity": 1 - results["distances"][0][i],
            })

        return formatted


def format_result(result: dict, index: int) -> str:
    """Formats a search result for human-readable display."""
    meta = result["metadata"]
    minutes = int(meta["start_time"] // 60)
    seconds = int(meta["start_time"] % 60)
    return (
        f"--- Result {index + 1} (similarity: {result['similarity']:.3f}) ---\n"
        f"Episode: {meta['episode_title']}\n"
        f"Time: {minutes:02d}:{seconds:02d}\n"
        f"Text: {result['text'][:300]}..."
    )


def run_query(query: str, n_results: int = 5):
    """
    Convenience function to run a query and print results.

    Args:
        query: Natural language query.
        n_results: Number of results to return.
    """
    searcher = SemanticSearcher()
    logger.info(f"\nQuery: {query}")

    results = searcher.search(query, n_results=n_results)

    print(f"\nFound {len(results)} results:\n")
    for i, result in enumerate(results):
        print(format_result(result, i))
        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_query(query)
    else:
        # Sample queries for testing
        sample_queries = [
            "missão Artemis e exploração espacial",
            "filmes de cinema",
            "quem é o Alexandre Ottoni",
        ]
        for q in sample_queries:
            run_query(q, n_results=3)
            print("=" * 60)