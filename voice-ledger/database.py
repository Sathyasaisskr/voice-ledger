"""Voice Ledger — database setup (SQLAlchemy + SQLite)"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ExpenseORM(Base):
    __tablename__ = "expenses"
    id          = Column(Integer, primary_key=True, index=True)
    amount      = Column(Float, nullable=False)
    category    = Column(String(64), nullable=False)
    description = Column(String(256), nullable=False)
    merchant    = Column(String(128), nullable=True)
    date        = Column(String(10), nullable=False)          # ISO-8601 date
    transcript  = Column(Text, nullable=True)
    source      = Column(String(16), default="voice")         # voice | manual
    created_at  = Column(DateTime, default=datetime.utcnow)


class QueryLogORM(Base):
    __tablename__ = "query_logs"
    id           = Column(Integer, primary_key=True, index=True)
    query        = Column(Text, nullable=False)
    rewritten    = Column(Text, nullable=True)
    response     = Column(Text, nullable=False)
    latency_ms   = Column(Float, nullable=True)
    tokens_used  = Column(Integer, nullable=True)
    model        = Column(String(64), nullable=True)
    run_id       = Column(String(64), nullable=True)          # MLflow run ID
    created_at   = Column(DateTime, default=datetime.utcnow)


class ObsLogORM(Base):
    __tablename__ = "obs_logs"
    id            = Column(Integer, primary_key=True, index=True)
    endpoint      = Column(String(64), nullable=False)
    prompt_hash   = Column(String(64), nullable=True)
    model         = Column(String(64), nullable=True)
    latency_ms    = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    comp_tokens   = Column(Integer, nullable=True)
    success       = Column(Boolean, default=True)
    run_id        = Column(String(64), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialised")
