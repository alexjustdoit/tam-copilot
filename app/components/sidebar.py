"""
Shared sidebar rendered from the entry point (streamlit_app.py).

Sidebar order is controlled by call order in streamlit_app.py:
  1. render_sidebar_header()        — branding, above nav
  2. st.sidebar.page_link() loop   — nav links
  3. pg.run()                       — page-specific controls (e.g. Eval Dashboard)
  4. render_sidebar_footer()        — LLM toggle, below everything

st.navigation() is called with position="hidden" so Streamlit does not inject
its own nav into the sidebar; we render nav links manually for full layout control.
"""
import os
import streamlit as st


_SIDEBAR_CSS = """<style>
[data-testid="stLogoSpacer"] {
    display: none !important;
}
[data-testid="stSidebarHeader"] {
    min-height: 0 !important;
    padding-bottom: 0 !important;
}
[data-testid="stSidebarContent"] {
    display: flex !important;
    flex-direction: column !important;
    min-height: 100vh !important;
}
[data-testid="stSidebarUserContent"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
    padding-top: 0.5rem !important;
}
[data-testid="stSidebarUserContent"] > div:first-child {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
}
[data-testid="stSidebarUserContent"] > div:first-child > [data-testid="stVerticalBlock"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
}
.element-container:has(.sidebar-footer-spacer) {
    flex: 1 !important;
    min-height: 0 !important;
}
</style>"""


def render_sidebar_header():
    with st.sidebar:
        st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)
        st.title("TAM Copilot")
        st.caption("AI-Powered Technical Account Management")
        st.divider()


def render_sidebar_footer():
    with st.sidebar:
        st.markdown('<div class="sidebar-footer-spacer"></div>', unsafe_allow_html=True)
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
