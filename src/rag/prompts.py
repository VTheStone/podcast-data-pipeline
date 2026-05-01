"""
Prompt templates for the RAG pipeline.
Centralized prompt management for easy iteration and testing.
"""

from src.ingestion.database import Episode


def format_chunk_for_context(chunk: dict, index: int) -> str:
    """
    Formats a single chunk for inclusion in the prompt context.

    Args:
        chunk: Search result dictionary with text and metadata.
        index: 1-based index for citation reference.

    Returns:
        Formatted chunk string.
    """
    meta = chunk["metadata"]
    minutes = int(meta["start_time"] // 60)
    seconds = int(meta["start_time"] % 60)
    time_str = f"{minutes:02d}:{seconds:02d}"

    return (
        f"[Trecho {index}]\n"
        f"Episódio: {meta['episode_title']}\n"
        f"Tempo: {time_str}\n"
        f"Conteúdo: {chunk['text']}\n"
    )


def build_context(chunks: list[dict]) -> str:
    """
    Builds the full context string from retrieved chunks.

    Args:
        chunks: List of search result dictionaries.

    Returns:
        Formatted context string with all chunks.
    """
    if not chunks:
        return "Nenhum trecho relevante encontrado."

    formatted = [format_chunk_for_context(c, i + 1) for i, c in enumerate(chunks)]
    return "\n---\n".join(formatted)


SYSTEM_PROMPT = """Você é um assistente especializado no podcast NerdCast do Jovem Nerd.

Seu papel é responder perguntas sobre o conteúdo dos episódios usando APENAS os trechos fornecidos.

Regras obrigatórias:
1. Use SOMENTE as informações dos trechos fornecidos. Nunca use conhecimento externo.
2. Cite a fonte de cada afirmação usando o formato [Trecho N, EP:MM:SS].
3. Se a informação não estiver nos trechos, responda: "Não encontrei essa informação nos episódios disponíveis."
4. Responda sempre em português brasileiro.
5. Seja direto e objetivo. Não repita a pergunta.
6. Se houver informações conflitantes entre trechos, mencione as diferentes perspectivas.

Formato de citação:
- Correto: "O Alexandre mencionou que... [Trecho 1, Ep: NerdCast 1026, 05:30]"
- Incorreto: "Segundo o podcast..." (sem citação específica)"""


def build_user_prompt(query: str, chunks: list[dict]) -> str:
    """
    Builds the user prompt combining context and query.

    Args:
        query: User's natural language question.
        chunks: List of retrieved chunks.

    Returns:
        Formatted user prompt string.
    """
    context = build_context(chunks)

    return f"""Trechos disponíveis:

{context}

Pergunta: {query}"""


def build_no_results_response() -> str:
    """Returns a standard response when no relevant chunks are found."""
    return (
        "Não encontrei trechos relevantes sobre esse tema nos episódios disponíveis. "
        "Tente reformular a pergunta ou pergunte sobre outro assunto do NerdCast."
    )