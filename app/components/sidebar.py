"""
Shared sidebar rendered on every page.
Import and call render_sidebar() at the top of each page.
"""
import os
import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.title("TAM Copilot")
        st.caption("AI-Powered Technical Account Management")

        st.divider()
        st.subheader("LLM Provider")
        use_local = st.toggle(
            "Use Local LLM (Ollama)",
            value=os.getenv("USE_LOCAL_LLM", "true").lower() == "true",
            help="Toggle between free local Ollama and API providers",
        )
        os.environ["USE_LOCAL_LLM"] = "true" if use_local else "false"

        if use_local:
            st.info("Local mode: Free, requires Ollama running")
        else:
            has_openai = bool(os.getenv("OPENAI_API_KEY"))
            has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
            if has_openai:
                st.success("OpenAI API key configured")
            else:
                st.warning("Set OPENAI_API_KEY in .env")
            if has_anthropic:
                st.success("Anthropic API key configured")

        st.divider()
        st.toggle("Dark Mode", key="dark_mode", value=st.session_state.get("dark_mode", False))
        st.caption("Toggle to match Streamlit's dark theme. Applies immediately on this page.")

        st.divider()
        st.caption("Stack: Python · Streamlit · Ollama · OpenAI · Anthropic")


def is_dark_mode() -> bool:
    return st.session_state.get("dark_mode", False)
