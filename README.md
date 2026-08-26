# AI Bug Investigation System

Existing bug-management systems primarily focus on recording, tracking, and
managing defects. This project extends that workflow with AI-driven
**investigation**: it understands a reported bug, generates reproduction
scenarios, predicts likely root causes, surfaces related historical bugs,
maps the blast radius across dependent modules, and recommends a targeted
regression testing strategy.

## Quick start

```bash
./run.sh
```

Then open **http://localhost:8000** in your browser.

(If you're not using the script: `pip install -r requirements.txt` then
`cd backend && python -m uvicorn app:app --reload`.)

The database (`backend/bugai.db`) is created and seeded automatically on
first run — no manual setup needed. Delete that file to reset to the demo
dataset.

## What it does (the pipeline)

For every bug report submitted through the dashboard:

1. **Understand the bug** — classifies which module the bug most likely
   belongs to, using explainable keyword matching (`ai/module_classifier.py`).
2. **Generate reproduction scenarios** — module-specific + generic
   edge-case templates (`ai/scenario_generator.py`).
3. **Predict root causes** — a transparent heuristic score combining
   keyword signal (60%) with historical frequency of that root cause for
   the module (40%) (`ai/root_cause_predictor.py`).
4. **Find related existing bugs** — TF-IDF + cosine similarity search over
   a historical bug corpus (`ai/similarity_search.py`).
5. **Identify impacted modules** — graph traversal (BFS/descendants) over
   a directed module-dependency graph built with `networkx`
   (`ai/impact_graph.py`).
6. **Recommend regression tests** — maps impacted modules to a tagged
   test-case catalogue and ranks by priority (`ai/regression_selector.py`).
7. **Bug → Impact Graph** — visualizes the dependency graph with the
   affected modules highlighted, rendered as inline SVG in the dashboard.

## Try it

Paste this into the dashboard to reproduce the motivating example:

- **Title:** Coupon discount lost after refresh at checkout
- **Description:** User applies a coupon, refreshes the page, then clicks
  checkout. The coupon still shows as applied in the UI but the discount
  is not reflected in the final charged amount, causing a session and
  cart state mismatch.

It should detect the **Coupon** module, surface **BUG-142** as ~80%+
similar, rank *"Coupon state not updated"* / *"Session/cart state
mismatch"* as top root causes, and recommend regression tests across
Coupon → Cart → Checkout → Payment → Order → Notification.

## Project structure

```
backend/
  app.py                     FastAPI app + API endpoints
  database.py                SQLite schema + seed data
  ai/
    module_classifier.py     Step 1: bug -> module
    scenario_generator.py    Step 2: reproduction scenarios
    root_cause_predictor.py  Step 3: root cause scoring
    similarity_search.py     Step 4: related bug search (TF-IDF)
    impact_graph.py          Step 5: dependency graph + traversal
    regression_selector.py   Step 6: regression test selection
frontend/
  index.html, style.css, app.js   Dashboard (vanilla JS, SVG graph)
```

## Honest notes on methodology (for your report / viva)

- **Root cause confidence %** is a transparent heuristic (keyword match +
  historical frequency), not a calibrated ML probability. This is stated
  explicitly in code comments and in the UI itself. It's designed to be
  fully explainable: every score can be traced back to which keywords
  fired and how many historical bugs support it.
- **Similarity search** (TF-IDF + cosine similarity) is a real, standard
  technique used in production duplicate-issue detectors — this is the
  most "defensible" AI component.
- **Impact graph** is deterministic graph traversal over a manually
  curated module-dependency graph. In a real system this graph would be
  inferred from API/service call graphs or code dependency analysis
  instead of hand-authored.
- **Module classification** and **scenario generation** are rule/template
  based for reliability and explainability in a demo setting. A natural
  extension (documented but not required) is to swap the classifier for
  an LLM call (e.g. the Anthropic API) for open-ended bug descriptions
  that don't hit the keyword bank.

## Extending it

- Swap `module_classifier.py`'s keyword matching for an LLM call for
  free-text descriptions with no keyword overlap.
- Replace `root_cause_predictor.py`'s heuristic with a model trained on
  labelled historical root-cause outcomes once you have enough data.
- Replace the hand-authored dependency graph in `database.py` with one
  inferred from your real system's API call graph or service map.
- Add authentication + a "confirm actual root cause" feedback loop so the
  historical-frequency signal improves over time.
