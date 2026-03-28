# Changelog

All notable changes to TAM Copilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
- Expansion Intelligence page (`8_Expansion_Intelligence.py`) — portfolio-wide expansion ranking table with heuristic scoring (seat utilization, DAU/MAU engagement, peer feature gaps, tier), plus per-account AI deep-dive using the existing `features/expansion.py` module
- Customer detail drill-down on the Customers page — select any account to see subscription info, DAU/MAU trend chart, features adopted/unadopted, open tickets table, and on-demand AI health assessment
- 7 new tests covering expansion schemas, `find_expansion_opportunities` provider wiring, `summarize_tag_trends` quality-provider enforcement, empty-tag edge case, and `taxonomy.py` round-trip/append behavior; 28/28 passing

### Fixed
- `eval/evaluator.py`: replaced `"resp" in dir()` guard with `resp = None` initialization + `resp is not None` check — previous pattern could incorrectly inherit latency/cost from the prior loop iteration when a case failed mid-eval
- `5_Eval_Dashboard.py`: stale caption updated from `GPT-4o-mini` to `GPT-5.4-nano`
- `README.md`: updated 4 stale `GPT-4o-mini` references to `GPT-5.4-nano`; fixture count corrected from 200 to 500 tickets

### Changed
- Sidebar layout restructured using `st.navigation(position="hidden")` + manual `st.page_link()` rendering: branding now appears above the page list, page-specific controls (e.g. Eval Dashboard provider selector) appear below it, and the LLM Provider toggle sits at the bottom
- Eval Dashboard and Technical Info moved into a collapsible **Developers** expander in the sidebar — they are not day-to-day TAM tools
- LLM status indicators downsized from colored info/success boxes to captions — less visual noise for a control meant to be out of the way
- Removed redundant "Navigate using the sidebar pages" caption from Overview page
- Removed "Provider Comparison Eval" paragraph from Overview — it is a developer tool, not a TAM-facing feature
- Moved LLM Provider Architecture table from Overview to Technical Info
- Overview feature descriptions now use "**Feature Name:** Description" format for visual clarity
- Overview top stats expanded from 4 to 6 metrics: added Triage Coverage % and ARR Renewing in 90 Days
- Overview now includes a **Needs Attention** section — accounts with open P1/P2 tickets, renewals within 60 days, or low seat utilization near renewal, sorted by severity
- `requirements.txt` minimum Streamlit version bumped to `>=1.36.0` (`position="hidden"` requires 1.36)

### Added (continued)
- Technical Info page (Developers section) — active provider config with live Ollama reachability check, pulled models list, environment variable reference table, quality routing rules, fixture data stats, eval framework CLI reference, stack versions, and links to GitHub and Ollama model library

### Fixed (pre-existing test failures)
- `test_triage_result_schema` and `test_triage_uses_quality_provider_for_p1`: `TicketTriageResult` grew a required `suggested_tags` field in 0.2.0 but these tests were never updated — both now pass

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
