"""
Voice Ledger — AI Finance Assistant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stack: FastAPI · OpenAI Whisper · GPT-4 · LangChain · Chroma · MLflow
Author: Portfolio Project
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import os

from database import init_db
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed demo data if DB is empty
    if settings.demo_mode:
        _seed_demo_data()
    print(f"🚀  Voice Ledger ready  |  demo_mode={settings.demo_mode}")
    yield
    print("👋  Voice Ledger stopped")


def _seed_demo_data():
    """Populate DB + Chroma with realistic demo expenses on first run."""
    from database import SessionLocal, ExpenseORM
    from services.rag_service import rag_service
    db = SessionLocal()
    try:
        if db.query(ExpenseORM).count() > 0:
            return
        SEED = [
            {"amount": 24.50, "category": "Food & Dining",    "description": "Lunch at Chipotle",          "merchant": "Chipotle",     "date": "2026-03-15", "source": "voice"},
            {"amount": 38.00, "category": "Transportation",   "description": "Uber ride to airport",        "merchant": "Uber",         "date": "2026-03-16", "source": "voice"},
            {"amount": 15.99, "category": "Subscriptions",    "description": "Netflix subscription",        "merchant": "Netflix",      "date": "2026-03-01", "source": "voice"},
            {"amount": 87.12, "category": "Food & Dining",    "description": "Grocery shopping",            "merchant": "Whole Foods",  "date": "2026-03-20", "source": "voice"},
            {"amount":  6.55, "category": "Food & Dining",    "description": "Coffee at Starbucks",         "merchant": "Starbucks",    "date": "2026-03-22", "source": "voice"},
            {"amount": 52.00, "category": "Transportation",   "description": "Gas fill-up",                 "merchant": "Shell",        "date": "2026-03-18", "source": "manual"},
            {"amount": 45.00, "category": "Fitness",          "description": "Monthly gym membership",      "merchant": "Planet Fitness","date": "2026-03-01", "source": "voice"},
            {"amount":139.00, "category": "Subscriptions",    "description": "Amazon Prime annual renewal", "merchant": "Amazon",       "date": "2026-03-05", "source": "voice"},
            {"amount": 62.00, "category": "Food & Dining",    "description": "Dinner at Olive Garden",      "merchant": "Olive Garden", "date": "2026-03-28", "source": "voice"},
            {"amount": 34.99, "category": "Education",        "description": "Python textbook on Amazon",   "merchant": "Amazon",       "date": "2026-03-10", "source": "manual"},
            {"amount":112.00, "category": "Utilities",        "description": "Monthly utilities bill",      "merchant": None,           "date": "2026-03-02", "source": "manual"},
            {"amount": 99.00, "category": "Shopping",         "description": "New headphones at Best Buy",  "merchant": "Best Buy",     "date": "2026-03-25", "source": "voice"},
            {"amount": 18.50, "category": "Food & Dining",    "description": "Sushi takeout",               "merchant": "Sakura Sushi", "date": "2026-04-01", "source": "voice"},
            {"amount": 29.99, "category": "Subscriptions",    "description": "Spotify Premium family",      "merchant": "Spotify",      "date": "2026-04-01", "source": "voice"},
            {"amount": 75.00, "category": "Healthcare",       "description": "Pharmacy — prescription",     "merchant": "CVS",          "date": "2026-04-03", "source": "voice"},
            {"amount": 11.99, "category": "Entertainment",    "description": "Movie ticket — AMC",          "merchant": "AMC",          "date": "2026-04-05", "source": "manual"},
            {"amount": 43.20, "category": "Food & Dining",    "description": "Weekly groceries",            "merchant": "Trader Joe's", "date": "2026-04-06", "source": "voice"},
            {"amount": 22.50, "category": "Transportation",   "description": "Lyft to downtown",            "merchant": "Lyft",         "date": "2026-04-07", "source": "voice"},
        ]
        for s in SEED:
            row = ExpenseORM(**s)
            db.add(row)
        db.commit()
        # Index all in Chroma
        for row in db.query(ExpenseORM).all():
            rag_service.index_expense(row.id, {
                "amount": row.amount, "category": row.category,
                "description": row.description, "merchant": row.merchant, "date": row.date,
            })
        print(f"🌱 Seeded {len(SEED)} demo expenses")
    finally:
        db.close()


app = FastAPI(
    title="Voice Ledger",
    description="Voice-first AI Finance Assistant — Whisper · GPT-4 · LangChain · Chroma · MLflow",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers ────────────────────────────────────────────────────────────────
from routers.voice    import router as voice_router
from routers.expenses import router as expenses_router
from routers.analytics import router as analytics_router
from routers.rag_router import router as rag_router

app.include_router(voice_router,     prefix="/api/voice",     tags=["Voice"])
app.include_router(expenses_router,  prefix="/api/expenses",  tags=["Expenses"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(rag_router,       prefix="/api/rag",       tags=["RAG"])

# ── Static + SPA ───────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    with open(os.path.join("static", "index.html")) as f:
        return f.read()

@app.get("/health")
async def health():
    return {"status": "ok", "demo_mode": settings.demo_mode}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))   # Railway injects $PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
