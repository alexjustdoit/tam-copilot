# TAM Copilot

AI-powered Technical Account Management dashboard built to demonstrate LLM engineering, structured outputs, cost-aware provider routing, and deep TAM/CSM domain knowledge.

[Demo the app on Streamlit!](https://tam-copilot.streamlit.app/)

![App screenshot](docs/screenshot.png) 

## Features

| Page | What it does |
|---|---|
| **Overview** | Morning briefing — portfolio stats, accounts needing attention (P1/P2 open, renewals, low utilization), ARR at renewal |
| **Customers** | Full portfolio table with risk flags; click any account for a detail view: usage trend chart, features adopted, open tickets, AI health score |
| **Ticket Triage** | Single-ticket AI triage: priority, sentiment, escalation risk, suggested response, accept/edit flows; batch triage scoped by customer, TAM, or full portfolio with one-click save |
| **Churn Risk** | Heuristic pre-ranking of at-risk accounts; per-account AI assessment with churn probability, risk factors, recommended actions, and outreach draft |
| **QBR Prep** | Generates executive-ready QBR talking points from 12 months of data — business wins, open risks, strategic asks, suggested agenda; downloadable as text |
| **Ticket Insights** | Tag frequency, volume by priority/category, trend over time, on-demand AI narrative, and full-text ticket search |
| **Management Insights** | TAM-level triage coverage, segment comparison matrix, tag heatmap (segment × tag), AI executive summary |
| **Expansion Intelligence** | Heuristic expansion score ranking (seat utilization, DAU/MAU, peer feature gaps); per-account AI opportunities with ARR uplift estimates and suggested pitches |

Developer tools (collapsible sidebar section):

| Page | What it does |
|---|---|
| **Eval Dashboard** | Run the 20-case labeled eval against any provider; side-by-side accuracy/latency/cost comparison |
| **Technical Info** | Live Ollama status, active provider config, env var reference, quality routing rules, fixture stats, stack versions |

## Architecture

```
LLM Router → Ollama (local, free)           ← development / cost-free demo
           → GPT-5.4-nano (OpenAI API)      ← production default (~$0.001/call)
           → Claude Haiku 4.5 (Anthropic)   ← quality tasks: P1 triage, QBR, insights
```

Provider selection is a single `.env` flag — no code changes needed to switch. Quality-sensitive tasks (`quality_required=True`) automatically upgrade to Claude when an Anthropic key is available, otherwise fall back to GPT-5.4-nano.

**Quality routing triggers:** P1 ticket triage, churn risk within 90 days of renewal, QBR generation, AI narrative summaries (tag insights, management insights).

## Quick Start

**Mac/Linux:**
```bash
git clone https://github.com/alexjustdoit/tam-copilot
cd tam-copilot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # edit: set USE_LOCAL_LLM and API keys
streamlit run app/streamlit_app.py
```

**Windows (Command Prompt or PowerShell):**
```bat
git clone https://github.com/alexjustdoit/tam-copilot
cd tam-copilot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app/streamlit_app.py
```

Fixture data (50 customers, 500 tickets, usage records, subscriptions) is committed — the app runs immediately with no seed step.

## Configuration

```bash
# .env
USE_LOCAL_LLM=true          # true → Ollama (free); false → OpenAI/Claude API
OLLAMA_BASE_URL=http://localhost:11434   # override for remote Ollama
OPENAI_API_KEY=sk-...       # required when USE_LOCAL_LLM=false
ANTHROPIC_API_KEY=sk-ant-...  # optional — enables quality routing to Claude
```

**Recommended workflow:** develop with `USE_LOCAL_LLM=true` (free, instant), flip to `false` before a demo or interview where output quality matters.

Demo session cost on GPT-5.4-nano: ~$0.05–0.20 total.

## Local LLM (Ollama)

```bash
# Install: https://ollama.com
ollama pull llama3.1:8b
ollama serve
```

Set `USE_LOCAL_LLM=true` in `.env`. All LLM calls are free and run on your machine.

## Tests

```bash
# Mac/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

pytest tests/ -v
```

28 tests covering data generators, LLM router, feature module schemas, provider wiring, tag insights, and taxonomy persistence.

## Eval

```bash
python eval/evaluator.py --providers openai,claude
python eval/evaluator.py --providers local   # requires Ollama
```

Runs a 20-case labeled ticket triage dataset against the specified providers and outputs accuracy, latency, and cost. Results are saved to `eval/results.json` and visible in the Eval Dashboard.

## Project Structure

```
tam-copilot/
├── app/
│   ├── streamlit_app.py        # entry point, navigation, Overview page
│   ├── components/sidebar.py   # shared sidebar (header + footer)
│   └── pages/                  # 8 main pages + 2 developer pages
├── features/                   # ticket_triage, health_score, churn_risk,
│                               # qbr_prep, expansion, tag_insights
├── llm/
│   ├── router.py               # USE_LOCAL_LLM routing + quality_required logic
│   └── providers/              # OllamaProvider, OpenAIProvider, ClaudeProvider
├── data/
│   ├── models.py               # Pydantic models (Customer, Ticket, Usage, Subscription)
│   ├── generators/             # Faker-based fixture generators
│   ├── fixtures/               # committed JSON — app works on fresh clone
│   ├── taxonomy.json           # tag/category vocabulary, grows as TAMs triage
│   └── taxonomy.py             # load/save helpers
├── eval/
│   ├── evaluator.py            # CLI eval runner
│   ├── metrics.py              # scoring logic (EvalReport, score_triage)
│   └── datasets/               # 20-case labeled JSONL dataset
└── tests/                      # pytest suite
```

## WSL2 Setup (Windows + GPU)

If you're running this on Windows with a GPU for Ollama:

**Prerequisites (Windows side):**
- WSL2 with Ubuntu: `wsl --install` in PowerShell (Admin), then reboot
- NVIDIA drivers: download from nvidia.com — no separate CUDA install needed in WSL2

**Inside WSL2:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# Clone and set up the project inside WSL2 (not on /mnt/c — performance matters)
cd ~
git clone https://github.com/alexjustdoit/tam-copilot
cd tam-copilot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run
ollama serve &
streamlit run app/streamlit_app.py --server.address 0.0.0.0
```

Access via the WSL2 IP printed at startup (not localhost) in your Windows browser. Find it anytime with `hostname -I | awk '{print $1}'`.

**Remote Ollama (desktop GPU → laptop):**
```bash
# On desktop WSL2:
OLLAMA_HOST=0.0.0.0 ollama serve

# On laptop .env:
OLLAMA_BASE_URL=http://<desktop-windows-ip>:11434
```

If the laptop can't reach the desktop, add a port proxy in Windows PowerShell (Admin):
```powershell
netsh interface portproxy add v4tov4 listenport=11434 listenaddress=0.0.0.0 connectport=11434 connectaddress=<wsl2-ip>
```

## Portfolio Talking Points

**LLM engineering**
- Provider abstraction layer — Ollama, OpenAI, and Anthropic behind a single interface; swap providers with one env var
- Structured outputs via Pydantic throughout — every LLM call returns a validated schema, not raw text
- Quality routing — high-stakes tasks (P1 triage, QBR, near-renewal churn) automatically upgrade to the best available model
- Eval framework — labeled dataset, reproducible scoring, side-by-side provider comparison on accuracy/latency/cost

**Product and domain depth**
- Covers the real TAM workflow end-to-end: triage → health → churn → QBR → expansion
- Batch triage scoped by customer, TAM, or full portfolio — reflects how a manager versus individual TAM would use the tool
- Tag taxonomy system that grows as TAMs use it, with similarity checks to prevent duplicates
- Overview built as a morning briefing (Needs Attention, renewal pipeline, triage coverage) rather than a feature demo

**Engineering decisions**
- Local-first development (Ollama, free) with a one-line switch to production APIs
- Fixture data committed to the repo so any reviewer can clone and run immediately
- 28-test suite covering generators, router logic, feature schemas, and file persistence
