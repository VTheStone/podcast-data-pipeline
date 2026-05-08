"""
Podcast Q&A — Streamlit web interface for the RAG pipeline.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
import streamlit as st

from config import settings
from src.rag.pipeline import RAGPipeline
from src.ui.translations import t


# Page configuration
st.set_page_config(
    page_title=t("PAGE_TITLE"),
    page_icon=t("PAGE_ICON"),
    layout="centered",
)


@st.cache_resource(show_spinner=t("LOADING_PIPELINE"))
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
    st.title(t("HEADER_TITLE"))
    st.caption(t("HEADER_CAPTION"))


def render_sidebar(pipeline: RAGPipeline):
    """Renders sidebar with system info and session controls."""
    with st.sidebar:
        st.header(t("SIDEBAR_SYSTEM_HEADER"))

        chunk_count = pipeline.searcher.collection.count()
        st.metric(t("SIDEBAR_CHUNKS_LABEL"), f"{chunk_count:,}")
        st.metric(t("SIDEBAR_LLM_LABEL"), settings.LLM_MODEL)

        st.divider()

        st.header(t("SIDEBAR_SESSION_HEADER"))

        total_tokens = sum(
            item.get("tokens_used", 0) for item in st.session_state.history
        )
        total_time = sum(
            item.get("elapsed", 0) for item in st.session_state.history
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric(t("SIDEBAR_QUESTIONS_LABEL"), len(st.session_state.history))
        with col2:
            st.metric(t("SIDEBAR_TOKENS_LABEL"), f"{total_tokens:,}")

        if total_time > 0:
            st.metric(t("SIDEBAR_TOTAL_TIME_LABEL"), f"{total_time:.1f}s")

        if st.button(t("NEW_CONVERSATION_BUTTON"), use_container_width=True):
            st.session_state.history = []
            st.session_state.pending_query = None
            st.rerun()

        st.divider()
        st.caption(t("SIDEBAR_FOOTER"))


def render_examples():
    """Renders clickable example queries when there's no history."""
    st.markdown(t("EXAMPLES_HEADER"))

    cols = st.columns(2)
    for i, example in enumerate(settings.EXAMPLE_QUERIES):
        col = cols[i % 2]
        with col:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state.pending_query = example
                st.rerun()


def render_message_pair(item: dict):
    """Renders a single Q&A pair from history."""
    with st.chat_message("user", avatar="❓"):
        st.write(item["query"])

    with st.chat_message("assistant", avatar="🎙️"):
        st.markdown(item["answer"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t("METRIC_TIME_LABEL"), f"{item['elapsed']:.1f}s")
        with col2:
            st.metric(t("METRIC_CHUNKS_USED_LABEL"), item["chunks_used"])
        with col3:
            st.metric(t("METRIC_TOKENS_LABEL"), f"{item.get('tokens_used', 0):,}")

    if item["sources"]:
        expander_label = t("SOURCES_EXPANDER_LABEL", count=len(item["sources"]))
        with st.expander(expander_label):
            for i, source in enumerate(item["sources"]):
                sim = source["similarity"]
                if sim >= 0.65:
                    sim_label = "🟢"
                elif sim >= 0.55:
                    sim_label = "🟡"
                else:
                    sim_label = "🔴"

                similarity_text = t("SIMILARITY_LABEL")
                st.markdown(
                    f"{sim_label} **{source['episode_title']}** "
                    f"[{source['time']}] — {similarity_text}: {sim}"
                )

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
    with st.spinner(t("SEARCHING_SPINNER")):
        start = time.time()

        chunks = pipeline.searcher.search(query, n_results=settings.RAG_N_CHUNKS)
        chunks = [c for c in chunks if c["similarity"] >= settings.RAG_MIN_SIMILARITY]

        result = pipeline.answer(query)
        elapsed = time.time() - start

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

    render_history()

    if not st.session_state.history:
        st.divider()
        render_examples()

    if st.session_state.pending_query:
        query = st.session_state.pending_query
        st.session_state.pending_query = None
        process_query(pipeline, query)
        st.rerun()

    if query := st.chat_input(t("CHAT_INPUT_PLACEHOLDER")):
        process_query(pipeline, query)
        st.rerun()


if __name__ == "__main__":
    main()