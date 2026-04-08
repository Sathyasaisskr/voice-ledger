"""
Analytics router — summary stats, category breakdown, monthly trend, observability metrics.
GET /api/analytics/summary
GET /api/analytics/categories
GET /api/analytics/monthly
GET /api/analytics/observability
"""
from typing import List
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db, ExpenseORM
from models import AnalyticsSummary, CategoryBreakdown, MonthlyTrend
from services.observability import obs_service
from config import settings

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(db: Session = Depends(get_db)):
    total      = db.query(func.sum(ExpenseORM.amount)).scalar() or 0.0
    count      = db.query(func.count(ExpenseORM.id)).scalar() or 0
    avg_exp    = (total / count) if count else 0.0

    today      = date.today()
    this_month = today.strftime("%Y-%m")
    last_month = (date(today.year, today.month - 1, 1) if today.month > 1
                  else date(today.year - 1, 12, 1)).strftime("%Y-%m")

    this_m_total = db.query(func.sum(ExpenseORM.amount)).filter(
        ExpenseORM.date.startswith(this_month)
    ).scalar() or 0.0

    last_m_total = db.query(func.sum(ExpenseORM.amount)).filter(
        ExpenseORM.date.startswith(last_month)
    ).scalar() or 0.0

    top_cat_row = (
        db.query(ExpenseORM.category, func.sum(ExpenseORM.amount).label("total"))
        .group_by(ExpenseORM.category)
        .order_by(func.sum(ExpenseORM.amount).desc())
        .first()
    )
    top_category = top_cat_row[0] if top_cat_row else "—"

    # Time saved: 3 min manual vs 20 sec voice
    voice_count = db.query(func.count(ExpenseORM.id)).filter(
        ExpenseORM.source == "voice"
    ).scalar() or 0
    time_saved = voice_count * (180 - 20)   # seconds saved per voice entry

    return AnalyticsSummary(
        total_expenses=round(total, 2),
        expense_count=count,
        avg_expense=round(avg_exp, 2),
        top_category=top_category,
        this_month_total=round(this_m_total, 2),
        last_month_total=round(last_m_total, 2),
        time_saved_seconds=float(time_saved),
        demo_mode=settings.demo_mode,
    )


@router.get("/categories", response_model=List[CategoryBreakdown])
def get_categories(db: Session = Depends(get_db)):
    rows = (
        db.query(
            ExpenseORM.category,
            func.sum(ExpenseORM.amount).label("total"),
            func.count(ExpenseORM.id).label("count"),
        )
        .group_by(ExpenseORM.category)
        .order_by(func.sum(ExpenseORM.amount).desc())
        .all()
    )
    return [CategoryBreakdown(category=r[0], total=round(r[1], 2), count=r[2]) for r in rows]


@router.get("/monthly", response_model=List[MonthlyTrend])
def get_monthly(db: Session = Depends(get_db)):
    rows = (
        db.query(
            func.substr(ExpenseORM.date, 1, 7).label("month"),
            func.sum(ExpenseORM.amount).label("total"),
            func.count(ExpenseORM.id).label("count"),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    return [MonthlyTrend(month=r[0], total=round(r[1], 2), count=r[2]) for r in rows]


@router.get("/observability")
def get_observability():
    """Return MLflow/in-memory observability metrics for the dashboard."""
    return obs_service.get_metrics_summary()
