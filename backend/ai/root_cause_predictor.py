"""
root_cause_predictor.py

IMPORTANT - honesty about methodology:
The "confidence %" produced here is a HEURISTIC score, not a statistically
calibrated probability from a trained ML model. It is computed from two
transparent, explainable signals:

  1. Keyword match strength  (does the bug description mention symptoms
     typically associated with this root cause?)
  2. Historical frequency    (how often has this root cause occurred for
     this module in the historical_bugs table?)

score = 0.6 * keyword_signal + 0.4 * historical_frequency_signal

This is intentionally simple and explainable so it can be defended in a
viva/demo: every number can be traced back to which keywords fired and how
many historical bugs support it. A real product would eventually replace
this with a model trained on labelled root-cause outcomes, but for a
final-year project an honest heuristic beats a fake-precision black box.
"""

from collections import Counter
from typing import List, Dict
import sqlite3

CAUSE_KEYWORDS = {
    "Coupon state not updated": ["coupon", "discount", "expired", "still applies", "stale"],
    "Checkout API failure": ["timeout", "api", "loading", "stuck", "fails", "error", "gateway"],
    "Session/cart state mismatch": ["refresh", "session", "logout", "switch account", "cache", "stale state", "mismatch"],
    "Race condition / missing debounce": ["double click", "double-click", "duplicate", "rapid", "simultaneous", "concurrent"],
    "Data validation gap": ["validation", "empty", "null", "missing field"],
}


def _keyword_signal(text: str, cause: str) -> float:
    text_lower = text.lower()
    keywords = CAUSE_KEYWORDS.get(cause, [])
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in text_lower)
    return min(hits / max(1, len(keywords)), 1.0)


def _historical_frequency_signal(conn: sqlite3.Connection, module: str, cause: str) -> float:
    cur = conn.cursor()
    cur.execute("SELECT root_cause FROM historical_bugs WHERE module = ?", (module,))
    causes = [r["root_cause"] for r in cur.fetchall()]
    if not causes:
        return 0.0
    counts = Counter(causes)
    return counts.get(cause, 0) / len(causes)


def predict_root_causes(conn: sqlite3.Connection, text: str, module: str, top_n: int = 3) -> List[Dict]:
    all_causes = set(CAUSE_KEYWORDS.keys())

    # also fold in any historical causes for this module that aren't in the keyword bank
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT root_cause FROM historical_bugs WHERE module = ?", (module,))
    for r in cur.fetchall():
        all_causes.add(r["root_cause"])

    results = []
    for cause in all_causes:
        kw_signal = _keyword_signal(text, cause)
        hist_signal = _historical_frequency_signal(conn, module, cause)
        score = 0.6 * kw_signal + 0.4 * hist_signal
        if kw_signal == 0 and hist_signal == 0:
            continue
        results.append({
            "cause": cause,
            "confidence_percent": round(score * 100),
            "keyword_signal": round(kw_signal, 2),
            "historical_signal": round(hist_signal, 2),
        })

    results.sort(key=lambda r: r["confidence_percent"], reverse=True)
    return results[:top_n] if results else [{
        "cause": "Insufficient signal - manual triage recommended",
        "confidence_percent": 0,
        "keyword_signal": 0,
        "historical_signal": 0,
    }]
