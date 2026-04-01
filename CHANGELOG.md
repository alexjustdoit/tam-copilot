# Changelog

All notable changes to TAM Copilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.1.1] — 2026-04-01

### Added
- QBR results cached to `qbr_cache.json` per customer — survives page navigation and app restarts; populated into session state on first page load
- QBR download button moved to top of page (next to Generate/Re-run) so it's accessible without scrolling; downloads as `.md` with full markdown formatting

### Fixed
- QBR TAM Summary generating as one long run-on bullet — added explicit one-fact-per-bullet instruction to system prompt
- Sidebar showing Streamlit's default auto-discovered nav ("streamlit app" link + all pages) after SCC reboot — removed `_initialized`/`st.rerun()` workaround that was causing sidebar content to be dropped; added CSS to unconditionally hide `[data-testid="stSidebarNav"]` regardless of `position="hidden"` timing

### Changed
- README: added cold-start note near the demo link explaining the Streamlit free tier sleep behavior

---

## [1.1.0] — 2026-04-01

### Added
- Per-session data isolation for Streamlit Community Cloud (`SCC_MODE=true`) — each visitor gets their own copy of fixture data in `data/sessions/{token}/` via URL query param token; triage saves, taxonomy changes, and tag edits never bleed between sessions
- **Reset Demo Data** button in sidebar (SCC only) — wipes session directory, clears token and state, restores stock fixture data instantly
- QBR **TAM Summary** — candid internal bullet points covering health signals, risks, renewal urgency, and relationship context; for pre-call prep
- QBR **Executive Summary** split from single string to list of polished talking points — positive/forward-looking but honest about major known issues

### Fixed
- Sidebar default nav flash on initial load — moved `st.navigation(position="hidden")` before `render_sidebar_header()` so Streamlit registers hidden nav before rendering the sidebar
- `SCC_MODE` env var not detected on Streamlit Cloud — switched from `os.getenv` to `st.secrets` with `os.getenv` fallback for local dev
- QBR generation truncated JSON error — increased Claude provider `max_tokens` from 1024 to 2048 to accommodate larger structured output

### Changed
- `load_data()` on all pages now accepts `fixtures_dir: str` parameter so `@st.cache_data` caches per session directory in SCC mode
- `data/taxonomy.py` is session-aware in SCC mode — reads/writes taxonomy from session directory instead of shared file

---

## [1.0.1] — 2026-03-28

### Added
- Persistent Segment and TAM Owner filters on every portfolio page (Overview, Customers, Churn Risk, Ticket Insights, Management Insights, Expansion Intelligence) — shared via session state, change once and all pages reflect it
- Segment filter added to Management Insights and Overview Needs Attention (were missing)
- Churn Risk assessment results cached in session state per customer — navigating away and back restores the last result instantly; button switches to "Re-run Assessment" when a cached result exists

### Fixed
- Filter persistence across page navigation — switched from Streamlit `key=` pattern to explicit `default=session_state` + write-back, which reliably restores selections after page switches
- Broken initial render when hard-refreshing on a deep-linked URL after server restart — immediate rerun on fresh session discards the broken first frame before it reaches the frontend

### Changed
- Page titles now match sidebar nav labels exactly: Customers, Ticket Triage, Churn Risk, QBR Preparation
- Renamed "Tier" → "Segment" in all filter labels and table columns across all pages
- Segment and TAM Owner filters are shared across pages via session state (`filter_segments`, `filter_tams`) — changing a filter on one page is reflected on all others
- Removed Provider / Latency metric from Churn Risk assessment output — not relevant to TAMs

---

## [1.0.0] — 2026-03-27

### Added
- Batch triage scoped by current customer, by TAM, or full portfolio — replaces the old per-customer-only batch section
- Batch triage now filters to un-triaged tickets only (open/in_progress with no tags)
- "Save All" button on batch results — writes all AI suggestions back in a single file pass via new `save_tickets_batch()`
- Batch results table includes Company and TAM columns when scope is broader than current customer

### Changed
- README fully rewritten to reflect v1 feature set, accurate project structure, condensed WSL2 setup, and expanded portfolio talking points

---

## [0.3.0] — 2026-03-27

### Added
- Expansion Intelligence page — portfolio-wide expansion ranking table with heuristic scoring (seat utilization, DAU/MAU engagement, peer feature gaps, tier), plus per-account AI deep-dive
- Customer detail drill-down on the Customers page — subscription info, DAU/MAU trend chart, features adopted/unadopted, open tickets table, and on-demand AI health assessment
- Technical Info page (Developers section) — active provider config, live Ollama status, environment variable reference, quality routing rules, fixture stats, eval CLI reference, stack versions
- 7 new tests covering expansion schemas, provider wiring, tag insights quality enforcement, and taxonomy persistence; 28/28 passing

### Fixed
- `eval/evaluator.py`: `resp = None` initialization replaces `"resp" in dir()` guard — previous pattern could inherit stale latency/cost from prior loop iteration on failed cases
- Stale `GPT-4o-mini` references updated to `GPT-5.4-nano` in Eval Dashboard and README

### Changed
- Sidebar layout restructured: branding above page list, Eval Dashboard and Technical Info moved into collapsible **Developers** expander, LLM status downsized to captions
- Overview expanded: Needs Attention table (P1/P2, renewals, low utilization), 6-metric stats row, feature descriptions with colons for visual separation
- LLM Provider Architecture table moved from Overview to Technical Info
- `requirements.txt` minimum Streamlit bumped to `>=1.36.0`

---

## [0.2.1] — 2026-03-26

### Fixed
- Churn Risk page: removed `background_gradient` on the Risk Score column — same matplotlib dependency error as in 0.2.0; replaced with plain `st.dataframe()`

### Changed
- Migrated to `st.navigation()` API to decouple sidebar labels from filenames
  - Home page now displays as **Overview** in the sidebar while `streamlit_app.py` retains its name and the run command is unchanged
  - All page labels (Customers, Ticket Triage, Churn Risk, etc.) are now defined explicitly in code rather than inferred from filenames
  - `st.set_page_config()` and `render_sidebar()` consolidated into the entry point — removed from all 7 individual page files
  - Developer comment added in `streamlit_app.py` (module docstring and inline above the page list) explaining the two-step process required to add new pages when `st.navigation()` is in use

---

## [0.2.0] — 2026-03-26

### Added
- Seed data expanded to 500 tickets (from 200), 44 templates across 8 categories (from 24), time window extended to 365 days
- Context modifier system: frustration, exec visibility, SLA risk, recurring issue, workaround, and blocker signals applied randomly to ~55% of tickets to create natural tag variety for triage
- Ticket Insights page (`6_ticket_insights.py`) — tag frequency, volume/priority charts, trend over time, on-demand AI narrative, and ticket search scoped to current segment/status filters
- Management Insights page (`7_management_insights.py`) — department-level view with triage coverage by TAM, segment comparison matrix, tag heatmap (segment × tag), and AI executive summary
- `features/tag_insights.py` — LLM narrative generator for both insights pages
- Tag taxonomy system (`data/taxonomy.json`) with 11 relationship/situational tags: Escalation Risk, Exec Visibility, Recurring Issue, Workaround Active, Blocked, Training Gap, Product Gap, Data Issue, SLA Risk, Churn Signal, QBR Worthy
- AI triage now suggests priority changes, category changes, and tags from the taxonomy
- Accept / Edit Manually flows on triage page — mutually exclusive, clearly separated
  - Accept: applies all AI suggestions and writes back to ticket data
  - Edit Manually: pre-populated with current ticket values (not AI suggestions), user selects from taxonomy or adds new entries
- Inline similarity check warns when a new tag/category is too close to an existing one
- AI can conservatively propose new tags/categories when none in the taxonomy fit
- New tags/categories added by users are persisted to `taxonomy.json` and available to the LLM in future triage sessions
- Tags field displayed in ticket details view

### Fixed
- Customer portfolio table: replaced background-color row highlighting (which was unreadable in dark mode) with theme-agnostic emoji risk indicators (🔴 P1/P2, 🟠 RENEWAL, 🟡 LOW-UTIL) in a dedicated Risk Flags column — no matplotlib or theme detection required
- Management Insights page: removed `background_gradient` calls on triage coverage and tag heatmap tables — pandas `.style.background_gradient()` requires matplotlib and fails at runtime; replaced with plain `st.dataframe()`
- `.env` not being loaded in `streamlit_app.py` — fixed by importing `config` at startup
- `.env` not being loaded in `eval/evaluator.py` — same fix
- `pytest` failing with `ModuleNotFoundError` — fixed by adding `conftest.py` to project root

### Changed
- Default OpenAI model upgraded from `gpt-4o-mini` to `gpt-5.4-nano`
- Cost constants in `openai_provider.py` updated to reflect gpt-5.4-nano pricing ($0.20/$1.25 per 1M tokens)
- Triage system prompt now injects current taxonomy at call time so the LLM always works with the latest tag/category vocabulary

---

## [0.1.0] — 2026-03-24

### Added
- Initial implementation
- Provider-agnostic LLM router: Ollama (local) ↔ GPT-4o-mini ↔ Claude Haiku 4.5
- Quality routing: P1 tickets and QBR prep auto-upgrade to Claude when `USE_LOCAL_LLM=false`
- Simulated fixture data: 50 customers, 200 tickets, 600 usage records, 50 subscriptions
- Features: Ticket Triage, Health Scoring, Churn Risk Detection, QBR Preparation, Expansion Intelligence
- Streamlit dashboard with 5 pages: Customer Portfolio, Ticket Triage, Churn Risk, QBR Prep, Eval Dashboard
- Eval framework: 20 labeled ticket triage cases, side-by-side accuracy/latency/cost comparison across providers
- 21 unit tests covering generators, LLM router, and feature modules
