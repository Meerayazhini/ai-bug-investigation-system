"""
database.py
Sets up the SQLite schema and seeds it with demo data:
- modules                 : the system's functional modules
- module_dependencies     : directed edges "module X can propagate a bug into module Y"
- historical_bugs         : past resolved bugs, used for similarity search + root-cause frequency
- test_cases              : regression test catalogue, tagged by module
- bug_reports             : bugs submitted through the tool (with the AI's findings attached)
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bugai.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS modules (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS module_dependencies (
    from_module_id  INTEGER NOT NULL REFERENCES modules(id),
    to_module_id    INTEGER NOT NULL REFERENCES modules(id),
    PRIMARY KEY (from_module_id, to_module_id)
);

CREATE TABLE IF NOT EXISTS historical_bugs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT UNIQUE NOT NULL,       -- e.g. BUG-142
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    module      TEXT NOT NULL,
    root_cause  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_cases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    module      TEXT NOT NULL,
    priority    TEXT NOT NULL               -- High / Medium / Low
);

CREATE TABLE IF NOT EXISTS bug_reports (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    detected_module     TEXT,
    root_causes_json     TEXT,
    scenarios_json       TEXT,
    related_bugs_json    TEXT,
    impacted_modules_json TEXT,
    regression_tests_json TEXT,
    strategy_json        TEXT,
    created_at          TEXT NOT NULL
);
"""


def seed_if_empty(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM modules")
    if cur.fetchone()["c"] > 0:
        return  # already seeded

    # ---- Modules -------------------------------------------------------
    modules = ["Coupon", "Cart", "Inventory", "Checkout", "Payment", "Order", "Notification"]
    for m in modules:
        cur.execute("INSERT INTO modules (name) VALUES (?)", (m,))

    name_to_id = {r["name"]: r["id"] for r in cur.execute("SELECT id, name FROM modules")}

    # ---- Dependency graph (directed: "bugs here can propagate to ->") --
    edges = [
        ("Coupon", "Cart"),
        ("Cart", "Checkout"),
        ("Inventory", "Checkout"),
        ("Checkout", "Payment"),
        ("Checkout", "Order"),
        ("Payment", "Order"),
        ("Order", "Notification"),
    ]
    for a, b in edges:
        cur.execute(
            "INSERT INTO module_dependencies (from_module_id, to_module_id) VALUES (?, ?)",
            (name_to_id[a], name_to_id[b]),
        )

    # ---- Historical bugs (used for similarity search + root-cause stats)
    historical = [
        ("BUG-101", "Cart total not recalculated after coupon removal",
         "When a user removes an applied coupon from the cart, the cart total still reflects the discounted price until the page is refreshed.",
         "Cart", "Stale cached state"),
        ("BUG-118", "Checkout button stuck in loading state on slow network",
         "On slow connections the checkout API call times out but the loading spinner never resets, blocking the user from retrying.",
         "Checkout", "Checkout API failure"),
        ("BUG-124", "Expired coupon still applies discount at checkout",
         "Coupons that expired minutes earlier are still accepted at checkout because the expiry check is only performed client-side.",
         "Coupon", "Coupon state not updated"),
        ("BUG-131", "Duplicate payment captured on double click",
         "Rapidly double-clicking the pay button triggers two payment capture calls before the button is disabled.",
         "Payment", "Race condition / missing debounce"),
        ("BUG-142", "Coupon discount lost after page refresh during checkout",
         "If a user applies a coupon and refreshes the page before clicking checkout, the discount is silently dropped but the coupon still shows as applied in the UI, causing a session/cart state mismatch.",
         "Coupon", "Session/cart state mismatch"),
        ("BUG-155", "Payment succeeds but order not created",
         "Payment gateway confirms success, but a timeout while writing the order record leaves the payment captured with no matching order.",
         "Order", "Checkout API failure"),
        ("BUG-160", "Inventory not decremented after successful order",
         "Stock count for purchased items is not reduced after checkout completes, leading to overselling.",
         "Inventory", "Session/cart state mismatch"),
        ("BUG-171", "Notification not sent for orders paid via saved card",
         "Order confirmation email fails to send specifically when payment is made using a previously saved card.",
         "Notification", "Checkout API failure"),
        ("BUG-183", "Cart shows old coupon after switching accounts",
         "Logging out and into a different account in the same browser tab shows the previous user's applied coupon still active.",
         "Cart", "Session/cart state mismatch"),
        ("BUG-190", "Checkout allows submission with empty cart after coupon error",
         "If applying a coupon throws a validation error, the cart empties silently but checkout can still be submitted.",
         "Coupon", "Coupon state not updated"),
    ]
    for code, title, desc, module, cause in historical:
        cur.execute(
            "INSERT INTO historical_bugs (code, title, description, module, root_cause, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (code, title, desc, module, cause, datetime.utcnow().isoformat()),
        )

    # ---- Regression test catalogue -------------------------------------
    tests = [
        ("Apply valid coupon and verify discount", "Coupon", "High"),
        ("Apply expired coupon is rejected", "Coupon", "High"),
        ("Remove coupon recalculates cart total", "Coupon", "High"),
        ("Coupon persists correctly across page refresh", "Coupon", "Medium"),
        ("Cart total matches sum of line items", "Cart", "High"),
        ("Cart state isolated per user session", "Cart", "High"),
        ("Add/remove item updates cart in real time", "Cart", "Medium"),
        ("Checkout completes with valid cart", "Checkout", "High"),
        ("Checkout blocked on empty cart", "Checkout", "High"),
        ("Checkout handles API timeout gracefully", "Checkout", "High"),
        ("Checkout re-validates cart state before submit", "Checkout", "High"),
        ("Payment capture is idempotent (no double charge)", "Payment", "High"),
        ("Payment failure rolls back order creation", "Payment", "High"),
        ("Saved card payment flow completes", "Payment", "Medium"),
        ("Order created only after payment confirmation", "Order", "High"),
        ("Order record matches captured payment amount", "Order", "High"),
        ("Inventory decremented after successful order", "Inventory", "High"),
        ("Notification sent for every completed order", "Notification", "Medium"),
    ]
    for name, module, priority in tests:
        cur.execute(
            "INSERT INTO test_cases (name, module, priority) VALUES (?, ?, ?)",
            (name, module, priority),
        )

    conn.commit()


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    seed_if_empty(conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
