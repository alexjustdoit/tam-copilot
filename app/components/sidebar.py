"""
Shared sidebar rendered from the entry point.

Call render_sidebar_header() before st.navigation() — renders the branding above the page list.
Call render_sidebar_footer() after pg.run() — renders the LLM toggle below page-specific controls.
"""
import os
import streamlit as st


def render_sidebar_header():
    with st.sidebar:
        st.title("TAM Copilot")
        st.caption("AI-Powered Technical Account Management")


def render_sidebar_footer():
    with st.sidebar:
        st.divider()
        st.subheader("LLM Provider")
        use_local = st.toggle(
            "Use Local LLM (Ollama)",
            value=os.getenv("USE_LOCAL_LLM", "true").lower() == "true",
            help="Toggle between free local Ollama and API providers",
        )
        os.environ["USE_LOCAL_LLM"] = "true" if use_local else "false"

        if use_local:
            st.caption("Local mode · Free · requires Ollama")
        else:
            has_openai = bool(os.getenv("OPENAI_API_KEY"))
            has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
            if has_openai:
                st.caption("✅ OpenAI key set")
            else:
                st.warning("Set OPENAI_API_KEY in .env")
            if has_anthropic:
                st.caption("✅ Anthropic key set")

        st.caption("Python · Streamlit · Ollama · OpenAI · Anthropic")
