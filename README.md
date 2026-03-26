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

This section walks through the full setup from scratch on a Windows machine. WSL2 (Windows Subsystem for Linux) gives you a real Linux environment inside Windows — it's required here because Ollama needs Linux to talk to the NVIDIA GPU.

---

### Step 1 — Enable WSL2 (run once, in Windows)

Open **PowerShell as Administrator** (right-click the Start menu → "Windows PowerShell (Admin)") and run:

```powershell
wsl --install
```

This installs WSL2 and Ubuntu automatically. When it finishes, **reboot your computer**.

> If you already have WSL but an older version, run `wsl --update` and `wsl --set-default-version 2` instead.

---

### Step 2 — Install NVIDIA GPU drivers for WSL2 (run once, in Windows)

For Ollama to use your GPU inside WSL2, you need the NVIDIA CUDA drivers installed on the **Windows side** (not inside WSL2 — Windows handles the GPU bridge automatically).

1. Go to: https://www.nvidia.com/download/index.aspx
2. Select your GPU model (e.g. GeForce RTX 4070) and download the latest Game Ready or Studio driver
3. Run the installer and follow the prompts
4. Reboot if prompted

> You do **not** need to install CUDA separately inside WSL2. The Windows driver exposes the GPU to WSL2 automatically.

---

### Step 3 — Open Ubuntu and finish first-time setup

After rebooting, search for **Ubuntu** in the Start menu and open it. The first time it opens, it will ask you to create a username and password — these are just for your Linux environment, they don't need to match your Windows login.

Once you're at the `$` prompt, update the package list:

```bash
sudo apt update && sudo apt upgrade -y
```

---

### Step 4 — Install Python inside WSL2

Ubuntu may come with Python pre-installed. Check:

```bash
python3 --version
```

If it prints `Python 3.x.x` you're good. If not:

```bash
sudo apt install python3 python3-pip python3-venv -y
```

Also make sure `pip` works:

```bash
pip3 --version
```

---

### Step 5 — Install Ollama inside WSL2

Run this single command inside your Ubuntu terminal — it downloads and installs Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Then pull the AI model:

```bash
ollama pull llama3.1:8b
```

This downloads about 4.7 GB — it only needs to happen once.

---

### Step 6 — Copy the project files into WSL2

**Important:** Keep the project files inside the WSL2 filesystem (not on your Windows `C:\` drive). Performance is dramatically better and some Python tools break on the Windows filesystem.

Your WSL2 home folder is `~/` (shorthand for `/home/yourusername/`). Copy the project there:

**Option A — you have the files on Windows already:**

Your Windows `C:\` drive is accessible inside WSL2 at `/mnt/c/`. For example, if the project is at `C:\Users\YourName\Documents\tam-copilot`:

```bash
cp -r "/mnt/c/Users/YourName/Documents/tam-copilot" ~/tam-copilot
cd ~/tam-copilot
```

Replace `YourName` with your actual Windows username.

**Option B — clone from Git:**

```bash
cd ~
git clone <your-repo-url> tam-copilot
cd tam-copilot
```

---

### Step 7 — Install Python dependencies (inside WSL2)

From inside the `tam-copilot` directory:

```bash
pip3 install -r requirements.txt
```

---

### Step 8 — Configure your .env file (inside WSL2)

```bash
cp .env.example .env
```

Open the file to edit it:

```bash
nano .env
```

Set `USE_LOCAL_LLM=true` and make sure `OLLAMA_BASE_URL=http://localhost:11434` (the default). Add your API keys for OpenAI/Anthropic if you have them. Press `Ctrl+O` then `Enter` to save, and `Ctrl+X` to exit.

---

### Step 9 — Start Ollama and run the app (inside WSL2)

Open **two Ubuntu terminal windows** (or tabs):

**Terminal 1 — start Ollama:**
```bash
ollama serve
```
Leave this running. You should see `Listening on 127.0.0.1:11434`.

**Terminal 2 — start the dashboard:**
```bash
cd ~/tam-copilot
streamlit run app/streamlit_app.py
```

Streamlit will print a URL like `http://localhost:8501`. Open that in your **Windows browser** (Chrome, Edge, etc.) — it works automatically because WSL2 bridges the network.

---

### Using the app from a separate laptop (remote Ollama)

If Ollama is running on a desktop with a GPU and you want to connect to it from a laptop on the same network:

**On the desktop — start Ollama bound to all interfaces (inside WSL2):**
```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

**Find the desktop's IP (inside WSL2):**
```bash
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
```

This prints something like `172.22.x.x` — that's the WSL2 internal IP. Use the **Windows host IP** instead (more reliable across reboots). Find it by running this in Windows PowerShell:

```powershell
ipconfig
```

Look for the "IPv4 Address" under your network adapter (e.g. `192.168.0.11`).

**On the laptop — set in `.env`:**
```
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://192.168.0.11:11434
```

> **Port forwarding note:** By default, WSL2 only listens internally. If the laptop can't reach the desktop's Ollama, run this in Windows PowerShell (Admin) on the desktop to forward the port:
> ```powershell
> netsh interface portproxy add v4tov4 listenport=11434 listenaddress=0.0.0.0 connectport=11434 connectaddress=<wsl2-internal-ip>
> ```
> Replace `<wsl2-internal-ip>` with what `ip addr` returned above.

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
