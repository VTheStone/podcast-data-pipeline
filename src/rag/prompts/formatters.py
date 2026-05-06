"""
Language-agnostic prompt formatting logic.
Uses language-specific labels loaded via the prompts package __init__.
"""

from src.rag.prompts import (
    CHUNK_LABEL,
    EPISODE_LABEL,
    TIME_LABEL,
    CONTENT_LABEL,
    NO_CHUNKS_FOUND,
    USER_PROMPT_TEMPLATE,
)


def format_chunk_for_context(chunk: dict, index: int) -> str:
    """
    Formats a single chunk for inclusion in the prompt context.

    Args:
        chunk: Search result dictionary with text and metadata.
        index: 1-based index for citation reference.

    Returns:
        Formatted chunk string with language-appropriate labels.
    """
    meta = chunk["metadata"]
    minutes = int(meta["start_time"] // 60)
    seconds = int(meta["start_time"] % 60)
    time_str = f"{minutes:02d}:{seconds:02d}"

    return (
        f"[{CHUNK_LABEL} {index}]\n"
        f"{EPISODE_LABEL}: {meta['episode_title']}\n"
        f"{TIME_LABEL}: {time_str}\n"
        f"{CONTENT_LABEL}: {chunk['text']}\n"
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
        return NO_CHUNKS_FOUND

    formatted = [format_chunk_for_context(c, i + 1) for i, c in enumerate(chunks)]
    return "\n---\n".join(formatted)


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
    return USER_PROMPT_TEMPLATE.format(context=context, query=query)