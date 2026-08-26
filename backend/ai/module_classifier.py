"""
module_classifier.py
Identifies which module(s) a free-text bug report most likely touches.

Method: weighted keyword matching against a per-module vocabulary.
This is intentionally transparent/explainable rather than a black-box model -
for a final year project, being able to show *why* a module was picked
(which keywords fired) is more defensible than an opaque score.
"""

from typing import List, Dict

MODULE_KEYWORDS: Dict[str, List[str]] = {
    "Coupon": ["coupon", "discount", "promo", "voucher"],
    "Cart": ["cart", "basket", "line item", "total", "subtotal"],
    "Inventory": ["inventory", "stock", "out of stock", "oversell"],
    "Checkout": ["checkout", "place order", "submit order", "buy now"],
    "Payment": ["payment", "pay", "charge", "card", "gateway", "transaction", "refund"],
    "Order": ["order", "confirmation", "invoice"],
    "Notification": ["notification", "email", "sms", "alert"],
}


def classify_module(text: str) -> Dict:
    """
    Returns the best-matching module plus a ranked breakdown of scores,
    so the UI can show *why* a module was chosen.
    """
    text_lower = text.lower()
    scores = {}
    matched_terms = {}

    for module, keywords in MODULE_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text_lower]
        if hits:
            scores[module] = len(hits)
            matched_terms[module] = hits

    if not scores:
        return {
            "primary_module": "Unclassified",
            "confidence_note": "No known module keywords matched; defaulting to manual triage.",
            "ranked": [],
        }

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    primary = ranked[0][0]

    return {
        "primary_module": primary,
        "matched_keywords": matched_terms.get(primary, []),
        "ranked": [
            {"module": m, "keyword_hits": s, "matched_terms": matched_terms[m]}
            for m, s in ranked
        ],
    }
