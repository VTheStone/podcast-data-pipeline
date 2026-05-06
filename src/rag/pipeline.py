"""
RAG pipeline for Phase 6.
Combines semantic search with LLM generation to answer questions
about the NerdCast podcast.
"""

from loguru import logger
from groq import Groq
from config import settings
from src.processing.searcher import SemanticSearcher
from src.rag.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    build_no_results_response,
)


class RAGPipeline:
    """
    End-to-end RAG pipeline for podcast Q&A.
    Maintains searcher and LLM client as singletons for performance.
    """

    def __init__(self):
        logger.info("Initializing RAG pipeline...")
        self.searcher = SemanticSearcher()
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
        logger.success("RAG pipeline ready")

    def answer(
        self,
        query: str,
        n_chunks: int = settings.RAG_N_CHUNKS,
        min_similarity: float = settings.RAG_MIN_SIMILARITY,
        episode_id: str = None,
    ) -> dict:
        """
        Answers a question using retrieved podcast content.

        Args:
            query: Natural language question.
            n_chunks: Number of chunks to retrieve.
            min_similarity: Minimum similarity score to include a chunk.
            episode_id: Optional filter to search within a specific episode.

        Returns:
            Dictionary with answer, sources and metadata.
        """
        logger.info(f"Query: {query}")

        # Step 1: Retrieve relevant chunks
        chunks = self.searcher.search(
            query=query,
            n_results=n_chunks,
            episode_id=episode_id,
        )

        # Filter by minimum similarity
        chunks = [c for c in chunks if c["similarity"] >= min_similarity]
        logger.info(f"Retrieved {len(chunks)} chunks above similarity threshold")

        # Handle no results
        if not chunks:
            return {
                "answer": build_no_results_response(),
                "sources": [],
                "chunks_used": 0,
                "model": settings.LLM_MODEL,
            }

        # Step 2: Build prompt
        user_prompt = build_user_prompt(query, chunks)

        # Step 3: Generate answer
        logger.info("Generating answer with LLM...")
        response = self.llm.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": settings.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        answer = response.choices[0].message.content

        # Step 4: Build sources list
        sources = []
        seen = set()
        for chunk in chunks:
            meta = chunk["metadata"]
            source_key = f"{meta['episode_id']}_{meta['chunk_index']}"
            if source_key not in seen:
                seen.add(source_key)
                minutes = int(meta["start_time"] // 60)
                seconds = int(meta["start_time"] % 60)
                sources.append({
                    "episode_title": meta["episode_title"],
                    "time": f"{minutes:02d}:{seconds:02d}",
                    "similarity": round(chunk["similarity"], 3),
                })

        logger.success(f"Answer generated using {len(chunks)} chunks")

        return {
            "answer": answer,
            "sources": sources,
            "chunks_used": len(chunks),
            "model": settings.LLM_MODEL,
            "tokens_used": response.usage.total_tokens,
        }


def run_interactive():
    """Runs an interactive Q&A session in the terminal."""
    pipeline = RAGPipeline()

    print("\n🎙️  NerdCast Q&A — Pergunte sobre os episódios!")
    print("Digite 'sair' para encerrar.\n")

    while True:
        query = input("Pergunta: ").strip()

        if query.lower() in ["sair", "exit", "quit"]:
            print("Encerrando...")
            break

        if not query:
            continue

        result = pipeline.answer(query)

        print(f"\n📝 Resposta:\n{result['answer']}")
        print(f"\n📚 Fontes ({result['chunks_used']} trechos):")
        for source in result["sources"]:
            print(f"  - {source['episode_title']} [{source['time']}] (sim: {source['similarity']})")
        print(f"\n🤖 Modelo: {result['model']} | Tokens: {result.get('tokens_used', 'N/A')}")
        print("-" * 60)


if __name__ == "__main__":
    run_interactive()