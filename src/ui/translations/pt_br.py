"""
Portuguese (Brazil) UI strings for the Streamlit app.
"""

# ============================================================================
# Page metadata
# ============================================================================

PAGE_TITLE = "{podcast_name} Q&A"
PAGE_ICON = "🎙️"
LOADING_PIPELINE = "Carregando pipeline RAG..."


# ============================================================================
# Header
# ============================================================================

HEADER_TITLE = "🎙️ {podcast_name} Q&A"
HEADER_CAPTION = (
    "Faça perguntas sobre os episódios do {podcast_name} e receba respostas "
    "baseadas nas transcrições, com fontes e timestamps."
)


# ============================================================================
# Sidebar
# ============================================================================

SIDEBAR_SYSTEM_HEADER = "⚙️ Sistema"
SIDEBAR_CHUNKS_LABEL = "Trechos disponíveis"
SIDEBAR_LLM_LABEL = "Modelo LLM"

SIDEBAR_SESSION_HEADER = "💬 Sessão"
SIDEBAR_QUESTIONS_LABEL = "Perguntas"
SIDEBAR_TOKENS_LABEL = "Tokens"
SIDEBAR_TOTAL_TIME_LABEL = "Tempo total"

NEW_CONVERSATION_BUTTON = "🗑️ Nova conversa"
SIDEBAR_FOOTER = "Projeto de portfólio — RAG sobre podcast {podcast_name}"


# ============================================================================
# Examples section
# ============================================================================

EXAMPLES_HEADER = "**💡 Exemplos de perguntas:**"


# ============================================================================
# Chat
# ============================================================================

CHAT_INPUT_PLACEHOLDER = "Faça uma pergunta sobre o {podcast_name}..."
SEARCHING_SPINNER = "🔍 Buscando nos episódios..."


# ============================================================================
# Message metrics
# ============================================================================

METRIC_TIME_LABEL = "Tempo"
METRIC_CHUNKS_USED_LABEL = "Trechos usados"
METRIC_TOKENS_LABEL = "Tokens"


# ============================================================================
# Sources
# ============================================================================

SOURCES_EXPANDER_LABEL = "📚 Ver {count} fontes utilizadas"
SIMILARITY_LABEL = "similaridade"