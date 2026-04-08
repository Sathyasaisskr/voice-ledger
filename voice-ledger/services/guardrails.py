"""
Guardrails — schema validation + content filters
Validates parsed expense dicts before they hit the database.
Implements bullet: output validation, schema checks, basic content filters.
"""
import re
from typing import Tuple, List, Dict, Any
from models import VALID_CATEGORIES


BAD_WORDS = {"hack", "fraud", "illegal", "launder"}  # minimal content filter

MAX_AMOUNT   = 100_000.0
MIN_AMOUNT   = 0.01
MAX_DESC_LEN = 256


def validate_expense(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Run all guardrail checks on a parsed expense dict.
    Returns (passed: bool, warnings: List[str]).
    """
    warnings: List[str] = []
    passed = True

    # ── Amount checks ──────────────────────────────────────────────────────────
    amount = data.get("amount")
    if amount is None:
        warnings.append("Amount is missing")
        passed = False
    elif not isinstance(amount, (int, float)):
        warnings.append(f"Amount type invalid: {type(amount)}")
        passed = False
    elif amount < MIN_AMOUNT or amount > MAX_AMOUNT:
        warnings.append(f"Amount ${amount} outside valid range [{MIN_AMOUNT}, {MAX_AMOUNT}]")
        passed = False

    # ── Category check ─────────────────────────────────────────────────────────
    category = data.get("category", "Other")
    if category not in VALID_CATEGORIES:
        warnings.append(f"Unknown category '{category}', defaulting to 'Other'")
        data["category"] = "Other"

    # ── Description check ──────────────────────────────────────────────────────
    desc = data.get("description", "")
    if not desc:
        warnings.append("Description is empty")
        passed = False
    elif len(desc) > MAX_DESC_LEN:
        data["description"] = desc[:MAX_DESC_LEN]
        warnings.append("Description truncated to 256 chars")

    # ── Content filter ─────────────────────────────────────────────────────────
    text = f"{desc} {data.get('merchant', '')}".lower()
    flagged = BAD_WORDS.intersection(text.split())
    if flagged:
        warnings.append(f"Content filter triggered: {flagged}")
        passed = False

    # ── Date format check ──────────────────────────────────────────────────────
    date_str = data.get("date", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        from datetime import date
        data["date"] = date.today().isoformat()
        warnings.append("Invalid date format — defaulted to today")

    return passed, warnings
