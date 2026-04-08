"""Voice Ledger — Pydantic request/response models"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime


# ── Expense ────────────────────────────────────────────────────────────────────
VALID_CATEGORIES = [
    "Food & Dining", "Transportation", "Shopping", "Entertainment",
    "Healthcare", "Utilities", "Housing", "Travel", "Education",
    "Subscriptions", "Fitness", "Gifts", "Other"
]

class ExpenseCreate(BaseModel):
    amount:      float
    category:    str
    description: str
    merchant:    Optional[str] = None
    date:        str                         # YYYY-MM-DD
    transcript:  Optional[str] = None
    source:      Optional[str] = "manual"

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v):
        if v <= 0 or v > 100_000:
            raise ValueError("Amount must be between $0.01 and $100,000")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in VALID_CATEGORIES:
            return "Other"
        return v


class ExpenseUpdate(BaseModel):
    amount:      Optional[float] = None
    category:    Optional[str]  = None
    description: Optional[str]  = None
    merchant:    Optional[str]  = None
    date:        Optional[str]  = None


class ExpenseOut(BaseModel):
    id:          int
    amount:      float
    category:    str
    description: str
    merchant:    Optional[str]
    date:        str
    transcript:  Optional[str]
    source:      str
    created_at:  datetime

    class Config:
        from_attributes = True


# ── Transcription ───────────────────────────────────────────────────────────────
class TranscribeResponse(BaseModel):
    transcript:  str
    confidence:  float
    demo_mode:   bool


class ProcessVoiceResponse(BaseModel):
    transcript:       str
    expense:          ExpenseOut
    guardrail_passed: bool
    warnings:         List[str]
    latency_ms:       float
    run_id:           Optional[str]


# ── RAG Query ───────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    answer:       str
    sources:      List[dict]
    rewritten:    str
    latency_ms:   float
    tokens_used:  Optional[int]
    run_id:       Optional[str]


# ── Analytics ───────────────────────────────────────────────────────────────────
class CategoryBreakdown(BaseModel):
    category: str
    total:    float
    count:    int

class MonthlyTrend(BaseModel):
    month:  str
    total:  float
    count:  int

class AnalyticsSummary(BaseModel):
    total_expenses:     float
    expense_count:      int
    avg_expense:        float
    top_category:       str
    this_month_total:   float
    last_month_total:   float
    time_saved_seconds: float           # 3 min manual → 20 sec voice
    demo_mode:          bool
