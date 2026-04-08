"""
Observability Service — MLflow lazy-loaded to reduce startup memory.
Falls back to in-memory buffer when MLflow is unavailable.
"""
import hashlib
import re
from typing import Optional, Dict, Any
from config import settings


class ObservabilityService:
    def __init__(self):
        self._mlflow = None
        self._experiment_id = None
        self._metrics_buffer: list = []
        # ── Lazy init — MLflow loaded on first log call, not at startup ────────
        print("ℹ️  Observability: lazy init (MLflow loads on first use)")

    def _ensure_mlflow(self):
        if self._mlflow is not None:
            return
        try:
            import mlflow
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
            exp = mlflow.get_experiment_by_name(settings.MLFLOW_EXPERIMENT)
            if exp is None:
                self._experiment_id = mlflow.create_experiment(settings.MLFLOW_EXPERIMENT)
            else:
                self._experiment_id = exp.experiment_id
            self._mlflow = mlflow
            print(f"✅ MLflow ready — experiment: {settings.MLFLOW_EXPERIMENT}")
        except Exception as e:
            print(f"⚠️  MLflow unavailable: {e}. Using in-memory buffer.")

    def _hash_prompt(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def log_transcription(self, run_id, latency_ms, confidence, demo):
        self._metrics_buffer.append({
            "endpoint": "transcription", "latency_ms": latency_ms,
            "confidence": confidence, "demo_mode": demo,
        })

    def log_expense_parse(self, run_id, transcript, result, latency_ms,
                          guardrail_passed, warnings, model):
        self._metrics_buffer.append({
            "endpoint": "expense_parse",
            "prompt_hash": self._hash_prompt(transcript),
            "model": model, "latency_ms": latency_ms,
            "guardrail_passed": guardrail_passed,
            "warning_count": len(warnings),
            "amount": result.get("amount", 0),
            "category": result.get("category", ""),
        })
        # Lazy log to MLflow
        try:
            self._ensure_mlflow()
            if self._mlflow:
                with self._mlflow.start_run(experiment_id=self._experiment_id,
                                             run_name="expense_parse"):
                    self._mlflow.log_metrics({
                        "parse_latency_ms": latency_ms,
                        "guardrail_passed": int(guardrail_passed),
                        "warning_count": len(warnings),
                    })
                    self._mlflow.log_params({
                        "prompt_hash": self._hash_prompt(transcript),
                        "model": model,
                    })
        except Exception:
            pass

    def log_rag_query(self, run_id, query, rewritten, answer,
                      latency_ms, tokens_used, model, sources_count):
        has_numbers = bool(re.search(r'\$[\d.]+|\d+\.\d+', answer))
        bias_flags = [kw for kw in ["always","never","everyone","nobody"]
                      if kw in answer.lower()]
        self._metrics_buffer.append({
            "endpoint": "rag_query", "latency_ms": latency_ms,
            "tokens_used": tokens_used, "sources_count": sources_count,
            "has_numbers": has_numbers, "bias_flags": bias_flags,
        })

    def get_metrics_summary(self) -> Dict[str, Any]:
        if not self._metrics_buffer:
            return {"total_calls": 0, "avg_latency_ms": 0,
                    "guardrail_pass_rate": 1.0, "models": []}
        calls = len(self._metrics_buffer)
        avg_lat = sum(e.get("latency_ms", 0) for e in self._metrics_buffer) / calls
        parse_calls = [e for e in self._metrics_buffer if e["endpoint"] == "expense_parse"]
        gpass = (sum(1 for e in parse_calls if e.get("guardrail_passed", True)) / len(parse_calls)
                 if parse_calls else 1.0)
        models = list({e.get("model", "demo") for e in self._metrics_buffer if e.get("model")})
        return {
            "total_calls": calls,
            "avg_latency_ms": round(avg_lat, 1),
            "guardrail_pass_rate": round(gpass, 3),
            "models": models,
        }


obs_service = ObservabilityService()
