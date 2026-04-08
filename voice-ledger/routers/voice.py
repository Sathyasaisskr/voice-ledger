"""
Voice router — transcribe audio + parse expense in one shot.
POST /api/voice/transcribe  → just transcription
POST /api/voice/process     → transcribe + parse + store
"""
import time
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, ExpenseORM
from models import TranscribeResponse, ProcessVoiceResponse, ExpenseOut
from services.transcription import transcription_service
from services.expense_parser import expense_parser
from services.rag_service import rag_service
from services.observability import obs_service
from config import settings

router = APIRouter()


class ParseTextRequest(BaseModel):
    transcript: str


@router.post("/parse-text", response_model=ProcessVoiceResponse)
async def parse_text(
    body: ParseTextRequest,
    db: Session = Depends(get_db),
):
    """
    Parse a plain text transcript (from Web Speech API) into a stored expense.
    No audio upload needed — browser handles transcription for free.
    """
    total_start = time.perf_counter()
    transcript = body.transcript.strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript is empty")

    expense_data, parse_latency, guardrail_passed, warnings = await expense_parser.parse(transcript)
    expense_data["transcript"] = transcript
    expense_data["source"]     = "voice"

    row = ExpenseORM(**expense_data)
    db.add(row); db.commit(); db.refresh(row)
    rag_service.index_expense(row.id, expense_data)

    total_ms = (time.perf_counter() - total_start) * 1000
    obs_service.log_expense_parse(
        run_id=None, transcript=transcript, result=expense_data,
        latency_ms=total_ms, guardrail_passed=guardrail_passed,
        warnings=warnings, model=settings.llm_model_label,
    )
    return ProcessVoiceResponse(
        transcript=transcript, expense=ExpenseOut.model_validate(row),
        guardrail_passed=guardrail_passed, warnings=warnings,
        latency_ms=total_ms, run_id=None,
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe uploaded audio file with Whisper."""
    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    transcript, confidence = await transcription_service.transcribe(
        audio_bytes, file.filename or "audio.webm"
    )
    return TranscribeResponse(
        transcript=transcript,
        confidence=confidence,
        demo_mode=settings.demo_mode,
    )


@router.post("/process", response_model=ProcessVoiceResponse)
async def process_voice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Full pipeline: audio → Whisper → GPT-4 parse → guardrails → DB → Chroma."""
    total_start = time.perf_counter()

    # 1. Transcribe
    audio_bytes = await file.read()
    transcript, confidence = await transcription_service.transcribe(
        audio_bytes, file.filename or "audio.webm"
    )

    # 2. Parse with LangChain + GPT-4
    expense_data, parse_latency, guardrail_passed, warnings = await expense_parser.parse(
        transcript
    )
    expense_data["transcript"] = transcript
    expense_data["source"]     = "voice"

    # 3. Store in SQLite
    row = ExpenseORM(**expense_data)
    db.add(row)
    db.commit()
    db.refresh(row)

    # 4. Index in Chroma for future RAG queries
    rag_service.index_expense(row.id, expense_data)

    # 5. Log to MLflow observability
    total_ms = (time.perf_counter() - total_start) * 1000
    obs_service.log_expense_parse(
        run_id=None,
        transcript=transcript,
        result=expense_data,
        latency_ms=total_ms,
        guardrail_passed=guardrail_passed,
        warnings=warnings,
        model=settings.GPT_MODEL if not settings.demo_mode else "demo",
    )

    return ProcessVoiceResponse(
        transcript=transcript,
        expense=ExpenseOut.model_validate(row),
        guardrail_passed=guardrail_passed,
        warnings=warnings,
        latency_ms=total_ms,
        run_id=None,
    )
