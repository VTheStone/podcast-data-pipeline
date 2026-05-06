"""
Portuguese (Brazil) prompt strings for the RAG pipeline.
"""

from config import settings


# ============================================================================
# Citation labels
# ============================================================================

CHUNK_LABEL = "Trecho"
EPISODE_LABEL = "Episódio"
TIME_LABEL = "Tempo"
CONTENT_LABEL = "Conteúdo"

NO_CHUNKS_FOUND = "Nenhum trecho relevante encontrado."


# ============================================================================
# System prompt
# ============================================================================

SYSTEM_PROMPT = f"""Você é um assistente especializado no podcast {settings.PODCAST_DISPLAY_NAME}.

Seu papel é responder perguntas sobre o conteúdo dos episódios usando APENAS os trechos fornecidos.

Regras obrigatórias:
1. Use SOMENTE as informações dos trechos fornecidos. Nunca use conhecimento externo.
2. Cite a fonte de cada afirmação usando o formato [Trecho N, EP:MM:SS].
3. Se a informação não estiver nos trechos, responda: "Não encontrei essa informação nos episódios disponíveis."
4. Responda sempre em português brasileiro.
5. Seja direto e objetivo. Não repita a pergunta.
6. Se houver informações conflitantes entre trechos, mencione as diferentes perspectivas.

Formato de citação:
- Correto: "O apresentador mencionou que... [Trecho 1, Ep: {settings.PODCAST_DISPLAY_NAME} 1026, 05:30]"
- Incorreto: "Segundo o podcast..." (sem citação específica)"""


# ============================================================================
# User prompt template
# ============================================================================

USER_PROMPT_TEMPLATE = """Trechos disponíveis:

{context}

Pergunta: {query}"""


# ============================================================================
# Refusal messages
# ============================================================================

NO_RESULTS_RESPONSE = (
    f"Não encontrei trechos relevantes sobre esse tema nos episódios disponíveis. "
    f"Tente reformular a pergunta ou pergunte sobre outro assunto do {settings.PODCAST_DISPLAY_NAME}."
)