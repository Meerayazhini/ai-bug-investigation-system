"""
impact_graph.py
Builds the module dependency graph from the DB and, given a module where a
bug originated, performs a downstream traversal (BFS) to find every module
that could plausibly be impacted.

Also exposes the full graph (nodes + edges) so the frontend can render it,
with the traversed/impacted nodes highlighted.
"""

from typing import List, Dict, Set
import sqlite3
import networkx as nx


def build_graph(conn: sqlite3.Connection) -> nx.DiGraph:
    g = nx.DiGraph()
    cur = conn.cursor()
    for r in cur.execute("SELECT name FROM modules"):
        g.add_node(r["name"])
    for r in cur.execute("""
        SELECT m1.name AS src, m2.name AS dst
        FROM module_dependencies d
        JOIN modules m1 ON d.from_module_id = m1.id
        JOIN modules m2 ON d.to_module_id = m2.id
    """):
        g.add_edge(r["src"], r["dst"])
    return g


def get_full_graph_json(conn: sqlite3.Connection, highlighted: Set[str] = None) -> Dict:
    g = build_graph(conn)
    highlighted = highlighted or set()
    return {
        "nodes": [{"id": n, "impacted": n in highlighted} for n in g.nodes()],
        "edges": [{"from": a, "to": b} for a, b in g.edges()],
    }


def get_impacted_modules(conn: sqlite3.Connection, origin_module: str) -> List[str]:
    g = build_graph(conn)
    if origin_module not in g:
        return []
    downstream = nx.descendants(g, origin_module)
    # origin module itself is always "impacted" (it's where the bug is)
    return [origin_module] + sorted(downstream)
