"""Voice Ledger — configuration & settings"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ── AI Provider ────────────────────────────────────────────────────────────
    # Priority: groq → google → openai → demo
    # Recommended free option: Google Gemini (just needs a Google account)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")   # FREE — aistudio.google.com
    GROQ_API_KEY:   str = os.getenv("GROQ_API_KEY",   "")   # FREE — console.groq.com
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")   # PAID — platform.openai.com

    # ── Models ─────────────────────────────────────────────────────────────────
    GEMINI_MODEL:       str = os.getenv("GEMINI_MODEL",        "gemini-1.5-flash")
    GROQ_LLM_MODEL:     str = os.getenv("GROQ_LLM_MODEL",     "llama-3.1-70b-versatile")
    GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL",  "whisper-large-v3")
    GPT_MODEL:          str = os.getenv("GPT_MODEL",           "gpt-4-turbo-preview")
    WHISPER_MODEL:      str = os.getenv("WHISPER_MODEL",       "whisper-1")
    EMBEDDING_MODEL:    str = os.getenv("EMBEDDING_MODEL",     "text-embedding-3-small")

    # ── Storage ────────────────────────────────────────────────────────────────
    DATABASE_URL:        str = os.getenv("DATABASE_URL",        "sqlite:///./voice_ledger.db")
    CHROMA_PERSIST_DIR:  str = os.getenv("CHROMA_PERSIST_DIR",  "./chroma_db")
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
    MLFLOW_EXPERIMENT:   str = os.getenv("MLFLOW_EXPERIMENT",   "voice-ledger")

    @property
    def provider(self) -> str:
        """
        'google' — Gemini 1.5 Flash, free (just Google account)
        'groq'   — LLaMA 3.1 70B, free (console.groq.com)
        'openai' — GPT-4, paid (~$3-5/month)
        'demo'   — intelligent mocks, no API needed
        """
        if self.GOOGLE_API_KEY: return "google"
        if self.GROQ_API_KEY:   return "groq"
        if self.OPENAI_API_KEY: return "openai"
        return "demo"

    @property
    def demo_mode(self) -> bool:
        return self.provider == "demo"

    @property
    def llm_model_label(self) -> str:
        labels = {
            "google": self.GEMINI_MODEL,
            "groq":   self.GROQ_LLM_MODEL,
            "openai": self.GPT_MODEL,
            "demo":   "demo",
        }
        return labels.get(self.provider, "demo")


settings = Settings()
