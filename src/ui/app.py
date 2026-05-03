"""
NerdCast Q&A — Streamlit web interface for the RAG pipeline.
Phase 7 milestone 2: rich interface with chat formatting and source details.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
import streamlit as st

from src.rag.pipeline import RAGPipeline
from src.ingestion.config import LLM_MODEL


# Page configuration
st.set_page_config(
    page_title="NerdCast Q&A",
    page_icon="🎙️",
    layout="centered",
)


@st.cache_resource(show_spinner="Carregando pipeline RAG...")
def load_pipeline() -> RAGPipeline:
    """Loads the RAG pipeline once and caches it across sessions."""
    return RAGPipeline()


def render_header():
    """Renders the page header and description."""
    st.title("🎙️ NerdCast Q&A")
    st.caption(
        "Faça perguntas sobre os episódios do NerdCast e receba respostas "
        "baseadas nas transcrições, com fontes e timestamps."
    )


def render_system_status(pipeline: RAGPipeline):
    """Renders system status information."""
    chunk_count = pipeline.searcher.collection.count()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Trechos disponíveis", f"{chunk_count:,}")
    with col2:
        st.metric("Modelo LLM", LLM_MODEL.split("-")[0].title())


def render_answer(result: dict, elapsed: float):
    """Renders the answer with metrics."""
    with st.chat_message("assistant", avatar="🎙️"):
        st.markdown(result["answer"])

        # Metrics row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tempo", f"{elapsed:.1f}s")
        with col2:
            st.metric("Trechos usados", result["chunks_used"])
        with col3:
            st.metric("Tokens", f"{result.get('tokens_used', 0):,}")


def render_sources(result: dict):
    """Renders sources as expandable cards with full text."""
    if not result["sources"]:
        return

    st.markdown("### 📚 Fontes utilizadas")

    # We need the full chunks (with text), so fetch from session state
    chunks = st.session_state.get("last_chunks", [])

    for i, source in enumerate(result["sources"]):
        title = source["episode_title"]
        time_str = source["time"]
        sim = source["similarity"]

        # Color code by similarity
        if sim >= 0.65:
            sim_label = "🟢"
        elif sim >= 0.55:
            sim_label = "🟡"
        else:
            sim_label = "🔴"

        with st.expander(
            f"{sim_label} **{title}** [{time_str}] — similaridade: {sim}"
        ):
            if i < len(chunks):
                st.markdown(f"_Trecho do episódio:_")
                st.write(chunks[i]["text"])
            else:
                st.caption("Texto do trecho não disponível.")


def render_welcome_message():
    """Shows welcome message with example queries when there's no query yet."""
    st.info(
        "👋 **Bem-vindo!** Pergunte qualquer coisa sobre os episódios do NerdCast.\n\n"
        "**Exemplos de perguntas:**\n"
        "- Quais astronautas participaram da missão Artemis II?\n"
        "- Qual a diferença entre a Artemis I e a Artemis II?\n"
        "- Por que voltar à Lua é importante?\n"
        "- O que falaram sobre o Senhor dos Anéis?"
    )


def process_query(pipeline: RAGPipeline, query: str):
    """Processes a query and renders the result."""
    # Show user message
    with st.chat_message("user", avatar="❓"):
        st.write(query)

    # Process with spinner
    with st.spinner("🔍 Buscando nos episódios..."):
        start = time.time()
        # Get raw chunks first to display in sources
        chunks = pipeline.searcher.search(query, n_results=5)
        chunks = [c for c in chunks if c["similarity"] >= 0.5]
        st.session_state["last_chunks"] = chunks

        # Then get the full answer
        result = pipeline.answer(query)
        elapsed = time.time() - start

    # Render answer
    render_answer(result, elapsed)

    # Render sources
    render_sources(result)


def main():
    render_header()

    pipeline = load_pipeline()

    render_system_status(pipeline)

    st.divider()

    # Query input
    query = st.text_input(
        "Sua pergunta:",
        placeholder="Ex: Quais astronautas participaram da Artemis II?",
        key="query_input",
    )

    # Show welcome or process query
    if not query:
        render_welcome_message()
    else:
        process_query(pipeline, query)


if __name__ == "__main__":
    main()