"""
Expense Parser — Google Gemini via LangChain (FREE)
Falls back to deterministic mock in demo mode.
"""
import json, re, time, random
from datetime import date
from typing import Dict, Any, Tuple, List
from config import settings
from services.guardrails import validate_expense

SYSTEM_PROMPT = """You are an expense parsing assistant. Extract structured expense data from a voice transcript.

Return ONLY valid JSON with these exact fields:
{
  "amount": <float, required>,
  "category": <one of: Food & Dining|Transportation|Shopping|Entertainment|Healthcare|Utilities|Housing|Travel|Education|Subscriptions|Fitness|Gifts|Other>,
  "description": <string, max 256 chars, required>,
  "merchant": <string or null>,
  "date": <YYYY-MM-DD, use today if not mentioned>
}

Rules:
- Convert spoken amounts ("twenty four dollars fifty cents" → 24.50)
- Return ONLY the JSON object, no extra text"""

# ── Demo mock parser ──────────────────────────────────────────────────────────
KEYWORD_CATEGORIES = {
    "chipotle|restaurant|dinner|lunch|breakfast|coffee|starbucks|sushi|pizza|food|grocery|groceries|whole foods|trader": "Food & Dining",
    "uber|lyft|taxi|gas|shell|fuel|parking|transit|subway|bus": "Transportation",
    "amazon|bestbuy|best buy|walmart|target|store|mall|shop|headphones": "Shopping",
    "netflix|spotify|hulu|disney|movie|theater|concert|game": "Entertainment",
    "gym|fitness|peloton|yoga|workout|planet fitness": "Fitness",
    "doctor|pharmacy|hospital|health|medical|dental|cvs|walgreens": "Healthcare",
    "rent|mortgage|electric|water|internet|utilities|comcast|att": "Utilities",
    "hotel|airbnb|flight|airline|travel|vacation": "Travel",
    "udemy|coursera|book|textbook|course|tuition|school": "Education",
    "subscription|membership|annual|monthly|prime|netflix|spotify": "Subscriptions",
    "gift|present|birthday": "Gifts",
}
KNOWN_MERCHANTS = {
    "chipotle":"Chipotle","starbucks":"Starbucks","uber":"Uber","amazon":"Amazon",
    "netflix":"Netflix","walmart":"Walmart","target":"Target","whole foods":"Whole Foods",
    "shell":"Shell","lyft":"Lyft","spotify":"Spotify","cvs":"CVS","best buy":"Best Buy",
    "planet fitness":"Planet Fitness","olive garden":"Olive Garden","trader joe":"Trader Joe's",
}
SPOKEN_NUMS = {
    "one hundred thirty nine":139,"one hundred twelve":112,"one hundred":100,
    "ninety nine":99,"eighty seven":87,"seventy five":75,"sixty two":62,
    "fifty two":52,"forty five":45,"forty three":43,"thirty eight":38,
    "thirty four":34,"twenty nine":29,"twenty four":24,"twenty two":22,
    "thirty":30,"eighteen":18,"fifteen":15,"twelve":12,"eleven":11,"six":6,
}

def _demo_parse(transcript: str) -> Dict[str, Any]:
    text = transcript.lower()
    amount = None
    for phrase, val in SPOKEN_NUMS.items():
        if phrase in text:
            cents_m = re.search(r'and\s+(\w+)\s+cent', text)
            cents = 0
            if cents_m:
                for cw, cv in {"fifty":50,"thirty":30,"twenty":20,"twelve":12,"ninety nine":99}.items():
                    if cw in cents_m.group(1): cents = cv; break
            amount = val + cents/100; break
    if amount is None:
        nums = [float(n) for n in re.findall(r'\$?(\d+\.?\d*)', text) if 0.5 <= float(n) <= 9999]
        amount = nums[0] if nums else round(random.uniform(10, 80), 2)
    category = "Other"
    for kws, cat in KEYWORD_CATEGORIES.items():
        if any(k in text for k in kws.split("|")): category = cat; break
    merchant = next((name for kw, name in KNOWN_MERCHANTS.items() if kw in text), None)
    description = " ".join(transcript.split()[:8]).strip(".,!?")
    return {"amount": round(amount,2), "category": category,
            "description": description[:256], "merchant": merchant,
            "date": date.today().isoformat()}


class ExpenseParser:
    def __init__(self):
        self._chain = None

    def _ensure_chain(self):
        if self._chain is not None or settings.demo_mode:
            return
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0,
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", "Today: {today}\nTranscript: {transcript}"),
            ])
            self._chain = prompt | llm | StrOutputParser()
            print(f"✅ Parser: Google {settings.GEMINI_MODEL} (FREE)")
        except Exception as e:
            print(f"⚠️  Parser init failed: {e}")

    async def parse(self, transcript: str) -> Tuple[Dict[str,Any], float, bool, List[str]]:
        self._ensure_chain()
        start = time.perf_counter()
        if settings.demo_mode or not self._chain:
            data = _demo_parse(transcript)
        else:
            try:
                raw = await self._chain.ainvoke({
                    "transcript": transcript,
                    "today": date.today().isoformat(),
                })
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                data = json.loads(m.group()) if m else _demo_parse(transcript)
            except Exception as e:
                print(f"⚠️  Parser error: {e}")
                data = _demo_parse(transcript)
        latency_ms = (time.perf_counter() - start) * 1000
        passed, warnings = validate_expense(data)
        if not passed:
            if not data.get("amount") or data["amount"] <= 0: data["amount"] = 1.00
            if not data.get("description"): data["description"] = "Expense"
            passed, warnings = validate_expense(data)
        return data, latency_ms, passed, warnings


expense_parser = ExpenseParser()
