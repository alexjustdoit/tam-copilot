# TAM Copilot

AI-powered Technical Account Management dashboard. Demonstrates LLM engineering, structured outputs, provider routing, and business domain knowledge for TAM/CSM/Solution Architect roles.

## What it does

| Feature | Description |
|---|---|
| **Ticket Triage** | Classify priority, detect sentiment, assess escalation risk, draft responses |
| **Health Scoring** | Composite 0–100 score from usage trends, support history, commercial signals |
| **Churn Risk** | At-risk account detection with specific risk factors and TAM actions |
| **QBR Prep** | Auto-generate executive-ready Quarterly Business Review talking points |
| **Expansion Finder** | Upsell/cross-sell signals from feature gap analysis |
| **Provider Eval** | Side-by-side accuracy/latency/cost benchmark: Ollama vs GPT-4o-mini vs Claude Haiku |

## Architecture

```
LLM Router → Ollama (local, free)
           → GPT-4o-mini (cheap API, default)
           → Claude Haiku 4.5 (quality tasks: P1 triage, QBR)
```

Provider selection is environment-driven. Dev uses Ollama (free). Production uses the cheapest viable API. Quality-required tasks (P1 tickets, QBR prep) auto-upgrade to Claude.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — set USE_LOCAL_LLM=true for Ollama, or add API keys

# 3. Generate demo data (runs instantly, committed fixtures also available)
python data/seed.py

# 4. Launch dashboard
streamlit run app/streamlit_app.py
```

## Local LLM Setup (Ollama)

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.1:8b
ollama serve   # starts on http://localhost:11434
```

Set `USE_LOCAL_LLM=true` in `.env`. All LLM calls are free.

## Windows Setup (WSL2)

Running on Windows? Use WSL2 — it gives a Linux environment with native NVIDIA GPU support, which is required for Ollama to use the GPU.

**One-time WSL2 setup (PowerShell as Administrator):**
```powershell
wsl --install   # installs Ubuntu; reboot when prompted
```

**Install NVIDIA CUDA drivers for WSL2:**
Download and install from: https://developer.nvidia.com/cuda/wsl

Then open the Ubuntu terminal and follow the standard Linux instructions below. Everything works as-is inside WSL2.

**Clone the repo inside WSL2** (not on the Windows filesystem — keep it in `~/` for performance):
```bash
git clone https://github.com/alexjustdoit/tam-copilot
cd tam-copilot
```

## Remote Ollama (e.g., desktop with GPU)

If running Ollama on a separate machine (e.g., a Windows desktop with an RTX 4070 running WSL2):

```bash
# Inside WSL2 on the desktop — bind Ollama to all interfaces:
OLLAMA_HOST=0.0.0.0 ollama serve

# Find the desktop's local IP (run in WSL2):
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1

# In .env on your laptop:
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://<desktop-wsl2-ip>:11434
```

> **Note:** The WSL2 IP can change on reboot. For a stable address, set a static IP in WSL2 or use the Windows host IP with port forwarding (`netsh interface portproxy` on the Windows side).

## API Keys (for cloud providers)

```bash
# .env
USE_LOCAL_LLM=false
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...   # optional
```

Demo session cost on GPT-4o-mini: **~$0.05–0.20 total**.

## Running Tests

```bash
pytest tests/ -v
```

## Running the Eval

```bash
# Compare providers on 20 labeled ticket triage cases
python eval/evaluator.py --providers openai,claude
python eval/evaluator.py --providers local   # requires Ollama
```

## Project Structure

```
tam-copilot/
├── data/           # Pydantic models, Faker generators, fixture JSON
├── llm/            # Provider abstraction (Ollama, OpenAI, Claude) + router
├── features/       # ticket_triage, health_score, churn_risk, qbr_prep, expansion
├── eval/           # Evaluator, scoring metrics, 20-case labeled dataset
├── app/            # Streamlit dashboard + 5 pages
└── tests/          # Unit tests for generators, router, features
```

## Portfolio Talking Points

- **LLM engineering**: Provider abstraction, structured outputs (Pydantic), prompt design, eval methodology
- **Cost-aware architecture**: Local-first dev, cheapest-viable-API production, quality routing for high-stakes tasks
- **Business domain knowledge**: TAM/CSM workflows, health scoring, QBR cycles, churn signals
- **Product thinking**: Usable Streamlit dashboard, not just scripts; real workflow coverage
- **Data engineering**: Realistic simulation with referential integrity across 50 customers
