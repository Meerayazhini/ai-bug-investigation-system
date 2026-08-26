"""
regression_selector.py
Given the list of impacted modules, pulls the relevant regression test
cases from the catalogue and produces a prioritized testing strategy:
"run these high-risk scenarios first, before retesting the reported bug."
"""

from typing import List, Dict
import sqlite3


def select_regression_tests(conn: sqlite3.Connection, impacted_modules: List[str]) -> List[Dict]:
    if not impacted_modules:
        return []
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in impacted_modules)
    cur.execute(
        f"SELECT name, module, priority FROM test_cases WHERE module IN ({placeholders})",
        impacted_modules,
    )
    rows = [dict(r) for r in cur.fetchall()]

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    rows.sort(key=lambda r: priority_rank.get(r["priority"], 3))
    return rows


def build_testing_strategy(impacted_modules: List[str], regression_tests: List[Dict], root_causes: List[Dict]) -> Dict:
    high_priority = [t for t in regression_tests if t["priority"] == "High"]
    top_cause = root_causes[0]["cause"] if root_causes else "Unknown"

    recommendation = (
        f"Before retesting the reported bug, execute the {min(5, len(high_priority))} "
        f"high-risk regression tests below first. The leading suspected root cause is "
        f"\"{top_cause}\", so prioritize scenarios that exercise state changes across "
        f"{', '.join(impacted_modules)}."
    )

    return {
        "recommendation": recommendation,
        "priority_run_first": high_priority[:5],
        "total_regression_tests": len(regression_tests),
        "impacted_module_count": len(impacted_modules),
    }
