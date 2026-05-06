"""
English prompt strings for the RAG pipeline.
Template for adapting the project to English-language podcasts.
"""

from config import settings


# ============================================================================
# Citation labels
# ============================================================================

CHUNK_LABEL = "Excerpt"
EPISODE_LABEL = "Episode"
TIME_LABEL = "Time"
CONTENT_LABEL = "Content"

NO_CHUNKS_FOUND = "No relevant excerpts found."


# ============================================================================
# System prompt
# ============================================================================

SYSTEM_PROMPT = f"""You are an assistant specialized in the {settings.PODCAST_DISPLAY_NAME} podcast.

Your role is to answer questions about episode content using ONLY the provided excerpts.

Mandatory rules:
1. Use ONLY information from provided excerpts. Never use external knowledge.
2. Cite sources for every claim using the format [Excerpt N, EP:MM:SS].
3. If the information isn't in the excerpts, respond: "I couldn't find this information in the available episodes."
4. Always respond in English.
5. Be direct and objective. Don't repeat the question.
6. If excerpts contain conflicting information, mention the different perspectives.

Citation format:
- Correct: "The host mentioned that... [Excerpt 1, Ep: {settings.PODCAST_DISPLAY_NAME} 1026, 05:30]"
- Incorrect: "According to the podcast..." (no specific citation)"""


# ============================================================================
# User prompt template
# ============================================================================

USER_PROMPT_TEMPLATE = """Available excerpts:

{context}

Question: {query}"""


# ============================================================================
# Refusal messages
# ============================================================================

NO_RESULTS_RESPONSE = (
    f"I couldn't find relevant excerpts about this topic in the available episodes. "
    f"Try rephrasing the question or ask about another {settings.PODCAST_DISPLAY_NAME} topic."
)