"""
similarity_search.py
Finds historically similar bugs using TF-IDF + cosine similarity over
(title + description) text. This is a real, defensible technique (not a
hand-tuned heuristic like the root-cause scorer) - it's the same family of
method used in many production "duplicate issue" detectors.
"""

from typing import List, Dict
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def find_similar_bugs(conn: sqlite3.Connection, query_text: str, top_n: int = 3, min_similarity: float = 0.15) -> List[Dict]:
    cur = conn.cursor()
    cur.execute("SELECT code, title, description, module, root_cause FROM historical_bugs")
    rows = cur.fetchall()
    if not rows:
        return []

    corpus_texts = [f"{r['title']} {r['description']}" for r in rows]
    corpus_texts.append(query_text)

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus_texts)

    query_vec = tfidf_matrix[-1]
    corpus_vecs = tfidf_matrix[:-1]
    similarities = cosine_similarity(query_vec, corpus_vecs)[0]

    scored = []
    for row, sim in zip(rows, similarities):
        if sim >= min_similarity:
            scored.append({
                "code": row["code"],
                "title": row["title"],
                "module": row["module"],
                "root_cause": row["root_cause"],
                "similarity_percent": round(float(sim) * 100),
            })

    scored.sort(key=lambda r: r["similarity_percent"], reverse=True)
    return scored[:top_n]
