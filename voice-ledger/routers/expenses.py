"""
Expenses router — full CRUD for expense records.
GET/POST/PUT/DELETE /api/expenses
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db, ExpenseORM
from models import ExpenseCreate, ExpenseUpdate, ExpenseOut
from services.rag_service import rag_service

router = APIRouter()


@router.get("/", response_model=List[ExpenseOut])
def list_expenses(
    limit:    int              = Query(50, le=200),
    offset:   int              = Query(0, ge=0),
    category: Optional[str]   = Query(None),
    month:    Optional[str]    = Query(None, description="YYYY-MM"),
    db:       Session          = Depends(get_db),
):
    """List expenses with optional category / month filters."""
    q = db.query(ExpenseORM)
    if category:
        q = q.filter(ExpenseORM.category == category)
    if month:
        q = q.filter(ExpenseORM.date.startswith(month))
    return q.order_by(desc(ExpenseORM.created_at)).offset(offset).limit(limit).all()


@router.post("/", response_model=ExpenseOut, status_code=201)
def create_expense(body: ExpenseCreate, db: Session = Depends(get_db)):
    """Manually create an expense."""
    row = ExpenseORM(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    rag_service.index_expense(row.id, body.model_dump())
    return row


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    row = db.query(ExpenseORM).filter(ExpenseORM.id == expense_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    return row


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, body: ExpenseUpdate, db: Session = Depends(get_db)):
    row = db.query(ExpenseORM).filter(ExpenseORM.id == expense_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    # Re-index in Chroma
    rag_service.delete_expense(expense_id)
    rag_service.index_expense(row.id, {
        "amount": row.amount, "category": row.category,
        "description": row.description, "merchant": row.merchant, "date": row.date,
    })
    return row


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    row = db.query(ExpenseORM).filter(ExpenseORM.id == expense_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    rag_service.delete_expense(expense_id)
    db.delete(row)
    db.commit()
