"""
Validation script for Phase 5 — Vector Indexing.
Generates a quality report of the ChromaDB index.
"""

from loguru import logger
from sqlalchemy.orm import Session
import chromadb

from config import settings
from src.ingestion.database import Episode, RAGChunk, get_engine


def validate_coverage(session: Session) -> dict:
    """Validates indexing coverage against chunked episodes."""
    total_chunked = session.query(Episode).filter(
        Episode.chunked == True
    ).count()
    total_indexed = session.query(Episode).filter(
        Episode.indexed == True
    ).count()
    pending = session.query(Episode).filter(
        Episode.chunked == True,
        Episode.indexed == False,
    ).count()

    return {
        "total_chunked": total_chunked,
        "total_indexed": total_indexed,
        "pending_indexing": pending,
        "coverage_pct": round(total_indexed / total_chunked * 100, 1) if total_chunked else 0,
    }


def validate_chroma_collection() -> dict:
    """Validates ChromaDB collection state."""
    try:
        client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        collection = client.get_collection(settings.CHROMA_COLLECTION_NAME)
        count = collection.count()

        # Get sample to validate metadata structure
        sample = collection.get(limit=1)
        has_metadata = bool(sample.get("metadatas") and sample["metadatas"][0])
        has_documents = bool(sample.get("documents") and sample["documents"][0])

        return {
            "collection_exists": True,
            "total_documents": count,
            "has_metadata": has_metadata,
            "has_documents": has_documents,
        }
    except Exception as e:
        return {
            "collection_exists": False,
            "error": str(e),
        }


def validate_consistency(session: Session, chroma_count: int) -> dict:
    """Validates consistency between SQL and ChromaDB."""
    sql_chunks = session.query(RAGChunk).filter(
        RAGChunk.embedding_id != None
    ).count()

    return {
        "sql_chunks_with_embedding_id": sql_chunks,
        "chroma_documents": chroma_count,
        "match": sql_chunks == chroma_count,
    }


def print_report(coverage: dict, chroma: dict, consistency: dict) -> None:
    """Prints formatted validation report."""
    logger.info("=" * 50)
    logger.info("PHASE 5 VALIDATION REPORT")
    logger.info("=" * 50)

    logger.info("--- Coverage ---")
    logger.info(f"Total chunked: {coverage['total_chunked']}")
    logger.info(f"Total indexed: {coverage['total_indexed']}")
    logger.info(f"Pending indexing: {coverage['pending_indexing']}")
    logger.info(f"Indexing coverage: {coverage['coverage_pct']}%")

    logger.info("--- ChromaDB Collection ---")
    if chroma["collection_exists"]:
        logger.info(f"Collection exists: ✓")
        logger.info(f"Total documents: {chroma['total_documents']}")
        logger.info(f"Has metadata: {chroma['has_metadata']}")
        logger.info(f"Has documents: {chroma['has_documents']}")
    else:
        logger.error(f"Collection error: {chroma.get('error')}")

    logger.info("--- SQL ↔ ChromaDB Consistency ---")
    logger.info(f"SQL chunks with embedding_id: {consistency['sql_chunks_with_embedding_id']}")
    logger.info(f"ChromaDB documents: {consistency['chroma_documents']}")
    logger.info(f"Counts match: {'✓' if consistency['match'] else '✗'}")

    logger.info("=" * 50)

    has_issues = (
        coverage['pending_indexing'] > 0 or
        not chroma.get('collection_exists', False) or
        not consistency['match']
    )

    if has_issues:
        logger.warning("VALIDATION STATUS: ISSUES FOUND - review warnings above")
    else:
        logger.success("VALIDATION STATUS: ALL CHECKS PASSED")


def run():
    """Main entry point for the Phase 5 validator."""
    engine = get_engine()

    chroma = validate_chroma_collection()

    with Session(engine) as session:
        coverage = validate_coverage(session)
        consistency = validate_consistency(
            session,
            chroma.get("total_documents", 0),
        )

    print_report(coverage, chroma, consistency)


if __name__ == "__main__":
    run()