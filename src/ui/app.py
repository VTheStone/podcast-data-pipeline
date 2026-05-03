"""
NerdCast Q&A — Streamlit web interface for the RAG pipeline.
Phase 7 milestone 3: chat history, clickable examples, session management.
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


# Page configuration
st.set_page_config(
    page_title="NerdCast Q&A",
    page_icon="🎙️",
    layout="centered",
)


EXAMPLE_QUERIES = [
    "Quais astronautas participaram da Artemis II?",
    "Qual a diferença entre Artemis I e Artemis II?",
    "O que falaram sobre o Senhor dos Anéis?",
    "Por que voltar à Lua é importante?",
]


@st.cache_resource(show_spinner="Carregando pipeline RAG...")
def load_pipeline() -> RAGPipeline:
    """Loads the RAG pipeline once and caches it across sessions."""
    return RAGPipeline()


def init_session_state():
    """Initializes session state variables on first load."""
    if "history" not in st.session_state:
        st.session_state.history = []
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None


def render_header():
    """Renders the page header and description."""
    st.title("🎙️ NerdCast Q&A")
    st.caption(
        "Faça perguntas sobre os episódios do NerdCast e receba respostas "
        "baseadas nas transcrições, com fontes e timestamps."
    )


def render_sidebar(pipeline: RAGPipeline):
    """Renders sidebar with system info and session controls."""
    with st.sidebar:
        st.header("⚙️ Sistema")

        chunk_count = pipeline.searcher.collection.count()
        st.metric("Trechos disponíveis", f"{chunk_count:,}")
        st.metric("Modelo LLM", "Llama 3.3 70B")

        st.divider()

        st.header("💬 Sessão")

        # Calculate session totals
        total_tokens = sum(
            item.get("tokens_used", 0) for item in st.session_state.history
        )
        total_time = sum(
            item.get("elapsed", 0) for item in st.session_state.history
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Perguntas", len(st.session_state.history))
        with col2:
            st.metric("Tokens", f"{total_tokens:,}")

        if total_time > 0:
            st.metric("Tempo total", f"{total_time:.1f}s")

        if st.button("🗑️ Nova conversa", use_container_width=True):
            st.session_state.history = []
            st.session_state.pending_query = None
            st.rerun()

        st.divider()

        st.caption("Projeto de portfólio — RAG sobre podcast NerdCast")


def render_examples():
    """Renders clickable example queries when there's no history."""
    st.markdown("**💡 Exemplos de perguntas:**")

    cols = st.columns(2)
    for i, example in enumerate(EXAMPLE_QUERIES):
        col = cols[i % 2]
        with col:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state.pending_query = example
                st.rerun()


def render_message_pair(item: dict):
    """Renders a single Q&A pair from history."""
    # User question
    with st.chat_message("user", avatar="❓"):
        st.write(item["query"])

    # Assistant answer
    with st.chat_message("assistant", avatar="🎙️"):
        st.markdown(item["answer"])

        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tempo", f"{item['elapsed']:.1f}s")
        with col2:
            st.metric("Trechos usados", item["chunks_used"])
        with col3:
            st.metric("Tokens", f"{item.get('tokens_used', 0):,}")

    # Sources
    if item["sources"]:
        with st.expander(f"📚 Ver {len(item['sources'])} fontes utilizadas"):
            for i, source in enumerate(item["sources"]):
                sim = source["similarity"]
                if sim >= 0.65:
                    sim_label = "🟢"
                elif sim >= 0.55:
                    sim_label = "🟡"
                else:
                    sim_label = "🔴"

                st.markdown(
                    f"{sim_label} **{source['episode_title']}** "
                    f"[{source['time']}] — similaridade: {sim}"
                )

                # Show chunk text if available
                if i < len(item.get("chunks", [])):
                    st.caption(item["chunks"][i]["text"])
                    if i < len(item["sources"]) - 1:
                        st.divider()


def render_history():
    """Renders all past Q&A pairs from session history."""
    for item in st.session_state.history:
        render_message_pair(item)


def process_query(pipeline: RAGPipeline, query: str):
    """Processes a query and adds it to history."""
    with st.spinner("🔍 Buscando nos episódios..."):
        start = time.time()

        # Get raw chunks for source display
        chunks = pipeline.searcher.search(query, n_results=5)
        chunks = [c for c in chunks if c["similarity"] >= 0.5]

        # Get full RAG answer
        result = pipeline.answer(query)
        elapsed = time.time() - start

    # Add to history
    st.session_state.history.append({
        "query": query,
        "answer": result["answer"],
        "sources": result["sources"],
        "chunks": chunks,
        "chunks_used": result["chunks_used"],
        "tokens_used": result.get("tokens_used", 0),
        "elapsed": elapsed,
    })


def main():
    init_session_state()
    pipeline = load_pipeline()

    render_header()
    render_sidebar(pipeline)

    # Render conversation history
    render_history()

    # Show examples if no history yet
    if not st.session_state.history:
        st.divider()
        render_examples()

    # Process pending query (from example click)
    if st.session_state.pending_query:
        query = st.session_state.pending_query
        st.session_state.pending_query = None
        process_query(pipeline, query)
        st.rerun()

    # Chat input at the bottom
    if query := st.chat_input("Faça uma pergunta sobre o NerdCast..."):
        process_query(pipeline, query)
        st.rerun()


if __name__ == "__main__":
    main()