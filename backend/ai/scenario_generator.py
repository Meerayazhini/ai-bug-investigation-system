"""
scenario_generator.py
Generates candidate reproduction scenarios for a bug, based on the module
it was classified into. Template bank per module + a couple of generic
"edge condition" templates that apply everywhere (refresh, network drop,
double-click, session switch).
"""

from typing import List, Dict

MODULE_SCENARIOS: Dict[str, List[str]] = {
    "Coupon": [
        "Apply a valid coupon -> proceed to checkout",
        "Apply an expired coupon -> proceed to checkout",
        "Apply a coupon -> remove it -> proceed to checkout",
        "Apply a coupon -> refresh the page -> proceed to checkout",
    ],
    "Cart": [
        "Add multiple items -> remove one -> verify total",
        "Add item -> switch user account in same tab -> verify cart",
        "Add item on one device -> open cart on another device",
    ],
    "Inventory": [
        "Purchase last unit in stock -> verify stock count",
        "Two users purchase the same last unit simultaneously",
        "Complete an order -> verify inventory decremented",
    ],
    "Checkout": [
        "Submit checkout with an empty cart",
        "Submit checkout while API response is delayed/timed out",
        "Submit checkout twice in rapid succession (double click)",
    ],
    "Payment": [
        "Double-click 'Pay Now' -> verify only one charge is captured",
        "Payment gateway times out -> verify order is not created",
        "Pay using a saved card -> verify confirmation is sent",
    ],
    "Order": [
        "Payment succeeds -> simulate order-write failure -> verify reconciliation",
        "Verify order amount matches captured payment amount",
    ],
    "Notification": [
        "Complete order -> verify confirmation email/SMS is sent",
        "Complete order using saved payment method -> verify notification fires",
    ],
}

GENERIC_EDGE_CASES = [
    "Repeat the reported flow after a page refresh",
    "Repeat the reported flow on a slow/unstable network",
    "Repeat the reported flow with rapid double-submission",
]


def generate_scenarios(module: str, max_scenarios: int = 6) -> List[str]:
    scenarios = list(MODULE_SCENARIOS.get(module, []))
    for edge in GENERIC_EDGE_CASES:
        if edge not in scenarios:
            scenarios.append(edge)
    return scenarios[:max_scenarios]
