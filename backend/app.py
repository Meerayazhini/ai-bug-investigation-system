import os
import sys
import json
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.append(os.path.dirname(__file__))

from database import init_db, get_connection
from ai.module_classifier import classify_module
from ai.scenario_generator import generate_scenarios
from ai.root_cause_predictor import predict_root_causes
from ai.similarity_search import find_similar_bugs
from ai.impact_graph import get_impacted_modules, get_full_graph_json
from ai.regression_selector import select_regression_tests, build_testing_strategy

app = FastAPI(title="AI Bug Investigation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


class BugReportIn(BaseModel):
    title: str
    description: str


@app.post("/api/analyze")
def analyze_bug(report: BugReportIn):
    conn = get_connection()
    full_text = f"{report.title} {report.description}"

    # 1. Understand the bug -> identify affected module
    classification = classify_module(full_text)
    module = classification["primary_module"]
    if module == "Unclassified":
        module = "Checkout"  # safe fallback so downstream steps still run

    # 2. Generate reproduction scenarios
    scenarios = generate_scenarios(module)

    # 3. Predict possible root causes
    root_causes = predict_root_causes(conn, full_text, module)

    # 4. Find related existing bugs
    related_bugs = find_similar_bugs(conn, full_text)

    # 5. Identify impacted modules + graph
    impacted_modules = get_impacted_modules(conn, module)
    graph = get_full_graph_json(conn, highlighted=set(impacted_modules))
    regression_tests = select_regression_tests(conn, impacted_modules)

    # 6. Testing strategy
    strategy = build_testing_strategy(impacted_modules, regression_tests, root_causes)

    result = {
        "classification": classification,
        "detected_module": module,
        "scenarios": scenarios,
        "root_causes": root_causes,
        "related_bugs": related_bugs,
        "impacted_modules": impacted_modules,
        "graph": graph,
        "regression_tests": regression_tests,
        "strategy": strategy,
    }

    conn.execute(
        """INSERT INTO bug_reports
           (title, description, detected_module, root_causes_json, scenarios_json,
            related_bugs_json, impacted_modules_json, regression_tests_json, strategy_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            report.title, report.description, module,
            json.dumps(root_causes), json.dumps(scenarios), json.dumps(related_bugs),
            json.dumps(impacted_modules), json.dumps(regression_tests), json.dumps(strategy),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return result


@app.get("/api/bugs")
def list_bug_reports():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, detected_module, created_at FROM bug_reports ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/graph")
def full_graph():
    conn = get_connection()
    graph = get_full_graph_json(conn)
    conn.close()
    return graph


@app.get("/api/historical-bugs")
def historical_bugs():
    conn = get_connection()
    rows = conn.execute("SELECT code, title, module, root_cause FROM historical_bugs").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- serve frontend --------------------------------------------------
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
