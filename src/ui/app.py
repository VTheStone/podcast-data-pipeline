"""
NerdCast Q&A — Streamlit web interface for the RAG pipeline.
Phase 7 milestone 1: basic setup and pipeline integration.
"""

import sys
from pathlib import Path

# Add project root to path so 'src' module can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.rag.pipeline import RAGPipeline


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


def main():
    st.title("🎙️ NerdCast Q&A")
    st.caption("Faça perguntas sobre os episódios do NerdCast")

    # Load pipeline (cached)
    pipeline = load_pipeline()

    # Pipeline status
    st.success(f"✅ Pipeline carregado | {pipeline.searcher.collection.count()} trechos disponíveis")

    # Basic query interface
    query = st.text_input(
        "Sua pergunta:",
        placeholder="Ex: Quais astronautas participaram da Artemis II?",
    )

    if query:
        with st.spinner("Buscando nos episódios..."):
            result = pipeline.answer(query)

        st.markdown("### 📝 Resposta")
        st.write(result["answer"])

        st.markdown("### 📚 Fontes")
        for source in result["sources"]:
            st.write(f"- **{source['episode_title']}** [{source['time']}] (similaridade: {source['similarity']})")


if __name__ == "__main__":
    main()