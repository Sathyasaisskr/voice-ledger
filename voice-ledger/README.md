# 🎙 Voice Ledger — AI Finance Assistant

> Voice-first expense tracker — **completely free to run forever**  
> Built with Whisper · LLaMA 3.1 · LangChain · Chroma · MLflow

---

## 💸 Cost: $0 Forever

| Service | Plan | Cost |
|---|---|---|
| **Groq API** | Free tier | $0 — 14,400 req/day |
| **Render** | Free tier | $0 — 750 hrs/month |
| **Chroma** | Local in container | $0 |
| **MLflow** | Local in container | $0 |
| **SQLite** | Local in container | $0 |
| **Frontend CDN** | Perplexity Computer | $0 |

---

## 🚀 Deploy in 15 Minutes (Completely Free)

### Step 1 — Get a FREE Groq API Key

1. Go to **[console.groq.com](https://console.groq.com)**
2. Click **Sign Up** (free, no credit card)
3. Go to **API Keys** → **Create API Key**
4. Copy the key — looks like: `gsk_xxxxxxxxxxxx`

> Groq gives you **Whisper Large v3** (transcription) + **LLaMA 3.1 70B** (LLM) free.  
> Limits: 14,400 requests/day — enough for years of personal use.

---

### Step 2 — Push to GitHub

```bash
cd voice-ledger

git init
git add .
git commit -m "Voice Ledger — AI finance assistant"

# Create a repo at github.com first, then:
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/voice-ledger.git
git push -u origin main
```

---

### Step 3 — Deploy on Render (Free)

1. Go to **[render.com](https://render.com)** → Sign up with GitHub (free)
2. Click **New** → **Web Service**
3. Connect your `voice-ledger` GitHub repo
4. Render auto-detects `render.yaml` — click **Create Web Service**
5. In the **Environment** tab, add:

   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | `gsk_xxxxxxxxxxxx` (your key from Step 1) |

6. Click **Manual Deploy** → **Deploy latest commit**
7. Build takes ~3 minutes
8. Copy your URL: `https://voice-ledger-xxxx.onrender.com`

---

### Step 4 — Connect Frontend

1. Open the live Voice Ledger frontend
2. Click **🔌 Connect Backend** in the sidebar
3. Paste your Render URL
4. Badge turns **🟢 LIVE — LLaMA 3.1 + Whisper**

---

## ⚠️ One Thing to Know About Render Free Tier

The service **sleeps after 15 minutes of inactivity** and takes ~30 seconds to wake up on first request. This is fine for a portfolio project — just open it a minute before a demo.

To avoid this: upgrade to Render Starter ($7/month) or use Railway Hobby ($5/month).

---

## 💻 Run Locally (Free)

```bash
cd voice-ledger
cp .env.example .env
# Add your GROQ_API_KEY to .env

pip install -r requirements.txt
python main.py
# Open http://localhost:8000
```

---

## 🏗️ Architecture

```
Voice (browser mic)
    │  WebM audio
    ▼
Groq Whisper Large v3   ← FREE transcription
    │  transcript text
    ▼
LangChain + LLaMA 3.1   ← FREE structured parsing
    │  {amount, category, merchant, date}
    ▼
Guardrails              ← schema checks + content filter
    │  validated expense
    ▼
SQLite + Chroma         ← storage + vector index (both FREE, local)
    │
    ▼
RAG Query Engine        ← query rewriting + ranking + clustering
    │  compressed context
    ▼
LLaMA 3.1 answer        ← FREE natural language response
    │
    ▼
MLflow observability    ← latency, guardrails, factuality, bias (FREE, local)
```

---

## 📁 Project Structure

```
voice-ledger/
├── main.py                    ← FastAPI entry + demo seed data
├── config.py                  ← Auto-detects provider: groq / openai / demo
├── database.py                ← SQLAlchemy (Expense, QueryLog, ObsLog)
├── models.py                  ← Pydantic schemas + guardrail validators
├── Dockerfile                 ← Production container
├── render.yaml                ← Render free tier config  ← USE THIS
├── railway.json               ← Railway alternative
├── requirements.txt           ← Includes groq + langchain-groq
├── .env.example               ← Copy to .env, add GROQ_API_KEY
├── routers/
│   ├── voice.py               ← POST /api/voice/process
│   ├── expenses.py            ← CRUD /api/expenses
│   ├── analytics.py           ← Stats, charts, observability
│   └── rag_router.py          ← POST /api/rag/query
└── services/
    ├── transcription.py       ← Groq Whisper / OpenAI Whisper / demo
    ├── expense_parser.py      ← LangChain + Groq LLaMA / GPT-4 / demo
    ├── rag_service.py         ← Chroma + Groq LLaMA / GPT-4 / demo
    ├── query_optimizer.py     ← Rewriting, ranking, clustering
    ├── guardrails.py          ← Schema + content filter
    └── observability.py       ← MLflow tracking
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ For free AI | Get free at console.groq.com |
| `OPENAI_API_KEY` | Optional | Only if you prefer GPT-4 (paid) |
| `GROQ_LLM_MODEL` | No | Default: `llama-3.1-70b-versatile` |
| `GROQ_WHISPER_MODEL` | No | Default: `whisper-large-v3` |
| `PORT` | No | Auto-injected by Render/Railway |

---

## 📊 API Endpoints

```
POST /api/voice/process     Audio → Whisper → LLaMA parse → stored
GET  /api/expenses/         List with filters (month, category)
POST /api/expenses/         Manual create
DELETE /api/expenses/{id}   Delete
GET  /api/analytics/summary Stats overview
GET  /api/analytics/categories  Category breakdown
GET  /api/analytics/monthly Monthly trend
POST /api/rag/query         Natural language query (RAG pipeline)
GET  /health                Health check
GET  /docs                  Swagger UI
```
