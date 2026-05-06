"""Retrieval over KBA and historical-incident indexes.

This module is the heart of the "no hallucination" promise:
    - retrieve_kbas() returns matches ONLY when cosine similarity is
      above the threshold in config.yaml. If nothing crosses the bar,
      it returns an empty list.
    - retrieve_similar_incidents() returns top-k by cosine — these become
      evidence for IT root-cause hypotheses.

Used by both src/generate.py and the Flask app.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.metrics.pairwise import cosine_similarity

from src.config import load_config
from src.data_loader import normalize_text


@dataclass
class KBAMatch:
    kb_number: str
    short_description: str
    introduction: str
    instructions_excerpt: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SimilarIncident:
    number: str
    short_description: str
    assignment_group: str
    business_service: str
    close_code: str
    close_notes_excerpt: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


# Cache loaders so the Flask app doesn't reload every request.
@lru_cache(maxsize=1)
def _load_kb_index() -> tuple[Any, Any, pd.DataFrame]:
    cfg = load_config()
    vec = joblib.load(cfg.paths.models_dir / "tfidf_kb.joblib")
    mat = sp.load_npz(cfg.paths.models_dir / "kb_matrix.npz")
    meta = pd.read_csv(cfg.paths.models_dir / "kb_meta.csv", low_memory=False)
    for col in ["short_description", "introduction", "instructions",
                "article_body"]:
        meta[col] = meta[col].fillna("").astype(str)
    return vec, mat, meta


@lru_cache(maxsize=1)
def _load_incident_index() -> tuple[Any, Any, pd.DataFrame]:
    cfg = load_config()
    vec = joblib.load(cfg.paths.models_dir / "tfidf_incident.joblib")
    mat = sp.load_npz(cfg.paths.models_dir / "incident_matrix.npz")
    meta = pd.read_csv(cfg.paths.models_dir / "incident_meta.csv",
                       low_memory=False)
    for col in ["short_description_clean", "close_notes_clean", "close_code",
                "assignment_group", "business_service"]:
        meta[col] = meta[col].fillna("").astype(str)
    return vec, mat, meta


def _excerpt(text: str, max_chars: int = 280) -> str:
    """Trim long text to a single-paragraph excerpt for templates."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def retrieve_kbas(
    query_text: str,
    top_k: int | None = None,
    threshold: float | None = None,
) -> list[KBAMatch]:
    """Return up to top_k KBAs whose cosine similarity exceeds threshold.

    If NO KBA exceeds the threshold, returns an empty list. Callers MUST
    check for this and surface "No strong KBA match found" in the UI.
    """
    cfg = load_config()
    top_k = top_k if top_k is not None else cfg.retrieval.kba_top_k
    threshold = threshold if threshold is not None else cfg.retrieval.kba_threshold

    if not query_text or not query_text.strip():
        return []

    vec, mat, meta = _load_kb_index()
    q_vec = vec.transform([normalize_text(query_text)])
    sims = cosine_similarity(q_vec, mat).ravel()

    # Take the top-k indices, then filter by threshold.
    top_idx = np.argsort(-sims)[:top_k]
    out: list[KBAMatch] = []
    for i in top_idx:
        score = float(sims[i])
        if score < threshold:
            continue
        row = meta.iloc[int(i)]
        out.append(KBAMatch(
            kb_number=str(row["kb_number"]),
            short_description=str(row["short_description"]),
            introduction=_excerpt(str(row["introduction"]), 400),
            instructions_excerpt=_excerpt(str(row["instructions"]), 600),
            score=round(score, 4),
        ))
    return out


def retrieve_similar_incidents(
    query_text: str,
    top_k: int | None = None,
) -> list[SimilarIncident]:
    """Return top-k closed-incident neighbors with their close_notes."""
    cfg = load_config()
    top_k = top_k if top_k is not None else cfg.retrieval.similar_incidents_top_k

    if not query_text or not query_text.strip():
        return []

    vec, mat, meta = _load_incident_index()
    q_vec = vec.transform([normalize_text(query_text)])
    sims = cosine_similarity(q_vec, mat).ravel()
    top_idx = np.argsort(-sims)[:top_k]

    out: list[SimilarIncident] = []
    for i in top_idx:
        row = meta.iloc[int(i)]
        out.append(SimilarIncident(
            number=str(row["number"]),
            short_description=str(row["short_description_clean"]),
            assignment_group=str(row["assignment_group"]),
            business_service=str(row["business_service"]),
            close_code=str(row["close_code"]),
            close_notes_excerpt=_excerpt(str(row["close_notes_clean"]), 400),
            score=round(float(sims[i]), 4),
        ))
    return out


def predict_assignment_group(query_text: str) -> dict:
    """Predict assignment group with top-3 probabilities."""
    cfg = load_config()
    vec = joblib.load(cfg.paths.models_dir / "tfidf_text_ag.joblib")
    clf = joblib.load(cfg.paths.models_dir / "clf_assignment_group.joblib")
    le = joblib.load(cfg.paths.models_dir / "label_encoder_ag.joblib")

    X = vec.transform([normalize_text(query_text)])
    probs = clf.predict_proba(X)[0]
    order = np.argsort(-probs)[:3]
    top = [
        {"label": le.classes_[i], "prob": round(float(probs[i]), 4)}
        for i in order
    ]
    return {"top1": top[0]["label"], "top1_prob": top[0]["prob"], "top3": top}


def predict_business_service(query_text: str) -> dict:
    """Predict business service with top-3 probabilities."""
    cfg = load_config()
    vec = joblib.load(cfg.paths.models_dir / "tfidf_text_bs.joblib")
    clf = joblib.load(cfg.paths.models_dir / "clf_business_service.joblib")
    le = joblib.load(cfg.paths.models_dir / "label_encoder_bs.joblib")

    X = vec.transform([normalize_text(query_text)])
    probs = clf.predict_proba(X)[0]
    order = np.argsort(-probs)[:3]
    top = [
        {"label": le.classes_[i], "prob": round(float(probs[i]), 4)}
        for i in order
    ]
    return {"top1": top[0]["label"], "top1_prob": top[0]["prob"], "top3": top}


if __name__ == "__main__":
    # Demo run on a fabricated incident text.
    q = "user cannot login to SAP system, getting authorization error S001"
    print(f"Query: {q}\n")

    print("Predicted assignment_group:")
    print(predict_assignment_group(q), "\n")

    print("Predicted business_service:")
    print(predict_business_service(q), "\n")

    print("KBA matches (above threshold):")
    matches = retrieve_kbas(q)
    if not matches:
        print("  (none — no strong KBA match found)")
    for m in matches:
        print(f"  {m.kb_number}  score={m.score}  {m.short_description[:80]}")

    print("\nSimilar historical incidents:")
    for si in retrieve_similar_incidents(q):
        print(f"  {si.number}  score={si.score}  {si.short_description[:80]}")
