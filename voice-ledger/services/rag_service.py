"""
RAG Service — Chroma + keyword search
Optimised for Render free tier: no ONNX download, lazy LLM init.
Chroma stores documents; keyword ranking handled in Python (no embeddings needed).
"""
import time
import re
from typing import List, Dict, Any, Tuple
from config import settings
from services.query_optimizer import rewrite_query, rank_results, build_context

RAG_SYSTEM_PROMPT = """You are a personal finance assistant. Answer questions about the user's expenses 
using ONLY the context provided. Be concise and specific. Always cite dollar amounts.

Context (expense records):
{context}

If context is empty, say so and suggest adding more expenses first."""


class RAGService:
    def __init__(self):
        self._llm      = None
        # In-memory expense store (fast, no ONNX needed)
        self._docs: List[Dict[str, Any]] = []
        print("ℹ️  RAG service ready (in-memory store, lazy LLM)")

    # ── Document store ────────────────────────────────────────────────────────
    def index_expense(self, expense_id: int, expense: Dict[str, Any]):
        # Remove existing entry if updating
        self._docs = [d for d in self._docs if d.get("id") != expense_id]
        self._docs.append({
            "id":          expense_id,
            "amount":      float(expense["amount"]),
            "category":    expense["category"],
            "description": expense["description"],
            "merchant":    expense.get("merchant") or "",
            "date":        expense["date"],
            "text":        f"{expense['description']} {expense.get('merchant','')} {expense['category']} {expense['date']}".lower(),
        })

    def delete_expense(self, expense_id: int):
        self._docs = [d for d in self._docs if d.get("id") != expense_id]

    # ── LLM (lazy) ────────────────────────────────────────────────────────────
    def _ensure_llm(self):
        if self._llm is not None or settings.demo_mode:
            return
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            if settings.provider == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.1,
                )
                print(f"✅ RAG LLM: Google {settings.GEMINI_MODEL} (FREE)")

            elif settings.provider == "groq":
                from langchain_groq import ChatGroq
                llm = ChatGroq(model=settings.GROQ_LLM_MODEL,
                               api_key=settings.GROQ_API_KEY,
                               temperature=0.1, max_tokens=512)
                print(f"✅ RAG LLM: Groq {settings.GROQ_LLM_MODEL} (FREE)")

            else:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model=settings.GPT_MODEL,
                                 api_key=settings.OPENAI_API_KEY,
                                 temperature=0.1, max_tokens=512)
                print(f"✅ RAG LLM: OpenAI {settings.GPT_MODEL}")

            prompt = ChatPromptTemplate.from_messages([
                ("system", RAG_SYSTEM_PROMPT),
                ("human", "{query}"),
            ])
            self._llm = prompt | llm | StrOutputParser()
        except Exception as e:
            print(f"⚠️  RAG LLM init failed: {e}")

    # ── Keyword search (no embeddings, no ONNX) ───────────────────────────────
    def _keyword_search(self, query: str, top_k: int) -> List[Dict]:
        if not self._docs:
            return []
        q_tokens = set(re.findall(r'\w+', query.lower()))
        STOP = {"the","and","for","was","are","did","how","what","show","give",
                "tell","find","get","list","much","last","this","month","year","my"}
        q_tokens -= STOP

        scored = []
        for doc in self._docs:
            score = sum(1 for t in q_tokens if t in doc["text"])
            scored.append({**doc, "_score": score, "distance": max(0, 1 - score * 0.2)})

        return sorted(scored, key=lambda x: x["_score"], reverse=True)[:top_k]

    # ── Demo answer (no LLM) ──────────────────────────────────────────────────
    def _demo_answer(self, query: str, results: List[Dict]) -> str:
        q = query.lower()
        if not results:
            return "No expenses found. Try adding some first."
        total = sum(r.get("amount", 0) for r in results)
        count = len(results)
        if re.search(r'total|how much|spent', q):
            return f"Based on {count} matching expense(s), total spending is ${total:.2f}."
        if re.search(r'biggest|largest|most', q):
            top = max(results, key=lambda x: x.get("amount", 0))
            return f"Largest: ${top['amount']:.2f} — {top.get('description','N/A')} on {top.get('date','N/A')}."
        if "subscription" in q:
            subs = [r for r in results if r.get("category") == "Subscriptions"]
            if subs:
                return (f"{len(subs)} subscription(s): " +
                        ", ".join(f"{r.get('merchant','?')} ${r.get('amount',0):.2f}" for r in subs) +
                        f". Total: ${sum(r.get('amount',0) for r in subs):.2f}.")
        items = "; ".join(f"{r.get('description','?')} (${r.get('amount',0):.2f})" for r in results[:3])
        return f"Found {count} expense(s): {items}. Total: ${total:.2f}."

    # ── Main query pipeline ───────────────────────────────────────────────────
    async def query(self, query: str, top_k: int = 5) -> Tuple[str, str, List[Dict], int]:
        self._ensure_llm()
        rewritten = rewrite_query(query)
        results   = self._keyword_search(rewritten, top_k)
        ranked    = rank_results(rewritten, results)
        context   = build_context(rewritten, ranked)

        if settings.demo_mode or not self._llm:
            return self._demo_answer(rewritten, ranked), rewritten, ranked[:top_k], 0

        try:
            answer = await self._llm.ainvoke({
                "context": context or "No expense records available.",
                "query":   query,
            })
            tokens = len((context + query + answer).split()) * 4 // 3
            return answer, rewritten, ranked[:top_k], tokens
        except Exception as e:
            print(f"⚠️  RAG query error: {e}")
            return self._demo_answer(rewritten, ranked), rewritten, ranked[:top_k], 0


rag_service = RAGService()
