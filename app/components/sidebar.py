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


_TAM_ICON_SVG = """
<div style="display:flex; justify-content:center; padding: 0.75rem 0 0.5rem 0;">
<svg width="52" height="44" viewBox="0 0 52 44" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="26" width="12" height="18" rx="2.5" fill="#4A90D9" opacity="0.55"/>
  <rect x="20" y="14" width="12" height="30" rx="2.5" fill="#4A90D9" opacity="0.75"/>
  <rect x="38" y="2" width="12" height="42" rx="2.5" fill="#4A90D9"/>
</svg>
</div>
"""

_SIDEBAR_CSS = """<style>
section[data-testid="stSidebar"] [data-testid="stLogoSpacer"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
    min-height: 0 !important;
    height: auto !important;
    padding: 0 !important;
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
        st.markdown(_TAM_ICON_SVG, unsafe_allow_html=True)
        st.title("TAM Copilot")
        st.caption("AI-Powered Technical Account Management")
        st.divider()


def render_sidebar_footer():
    with st.sidebar:
        st.markdown('<div class="sidebar-footer-spacer"></div>', unsafe_allow_html=True)
        st.divider()
        scc_mode = str(st.secrets.get("SCC_MODE", os.getenv("SCC_MODE", "false"))).lower() == "true"

        st.subheader("LLM Provider")
        if scc_mode:
            st.toggle(
                "Use Local LLM (Ollama)",
                value=False,
                disabled=True,
                help="Local Ollama is not available on the hosted demo — the app uses OpenAI (standard tasks) and Anthropic Claude (quality tasks) automatically.",
            )
            st.caption("Demo uses OpenAI + Anthropic · Local Ollama available when self-hosted")
        else:
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


        if scc_mode:
            st.divider()
            st.markdown("""<style>
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    border: 1px solid #e74c3c !important;
    letter-spacing: 0.01em;
}
</style>""", unsafe_allow_html=True)
            if st.button("↺\u2002Reset Demo Data", use_container_width=True, help="Restore stock fixture data and start a fresh session"):
                from data.session_store import reset_session
                reset_session()
                st.rerun()
