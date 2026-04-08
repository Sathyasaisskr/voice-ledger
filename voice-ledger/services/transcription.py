"""
Transcription Service
Web Speech API handles transcription in the browser (FREE, no API key).
This service is a fallback for direct audio uploads only.
"""
import random
from typing import Tuple
from config import settings

DEMO_TRANSCRIPTS = [
    "I spent twenty four dollars and fifty cents at Chipotle for lunch today",
    "Paid thirty eight dollars for an Uber ride to the airport",
    "Netflix subscription renewed for fifteen ninety nine this month",
    "Bought groceries at Whole Foods for eighty seven dollars",
    "Coffee at Starbucks was six fifty five",
    "Filled up the car with gas spent fifty two dollars at Shell",
    "Gym membership payment of forty five dollars",
    "Bought new headphones for ninety nine dollars at Best Buy",
    "Dinner at Olive Garden cost sixty two dollars including tip",
    "Pharmacy prescription at CVS for seventy five dollars",
]


class TranscriptionService:
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> Tuple[str, float]:
        """
        Returns a demo transcript.
        Real transcription happens via Web Speech API in the browser — no API key needed.
        """
        transcript = random.choice(DEMO_TRANSCRIPTS)
        print("🎤 [Browser Web Speech API handles transcription — this is fallback demo]")
        return transcript, 0.92


transcription_service = TranscriptionService()
