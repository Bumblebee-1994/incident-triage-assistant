"""Build a TF-IDF index over historical CLOSED incidents for similarity retrieval.

We index only training-split closed incidents to avoid leaking val/test
incidents into the demo's "similar incidents" panel. close_notes from those
neighbors become evidence for IT root-cause hypotheses.

Run as a script:
    python -m src.build_incident_index

Outputs:
    models/tfidf_incident.joblib
    models/incident_matrix.npz
    models/incident_meta.csv
"""
from __future__ import annotations

import joblib
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import load_config


def main() -> None:
    cfg = load_config()

    print("Loading incidents and train split...")
    inc = pd.read_csv(cfg.paths.processed_dir / "incidents_clean.csv",
                      low_memory=False)
    train_ids = set(pd.read_csv(cfg.paths.splits_dir / "train.csv")["number"])

    # Use only training-split incidents that are closed and have close notes,
    # since their close_notes are the supervision signal for resolution.
    df = inc[inc["number"].isin(train_ids)].copy()
    df = df[df["state"].astype(str).str.lower() == "closed"]
    df = df[df["close_notes_clean"].fillna("").astype(str).str.len() > 5]
    df = df.reset_index(drop=True)
    df["text"] = df["text"].fillna("").astype(str)
    print(f"  closed train incidents with notes: {len(df):,}")

    print("Fitting TF-IDF on incident text...")
    vectorizer = TfidfVectorizer(
        max_features=cfg.tfidf.max_features,
        ngram_range=tuple(cfg.tfidf.ngram_range),
        min_df=cfg.tfidf.min_df,
        max_df=cfg.tfidf.max_df,
        sublinear_tf=cfg.tfidf.sublinear_tf,
        strip_accents=cfg.tfidf.strip_accents,
        lowercase=True,
    )
    matrix = vectorizer.fit_transform(df["text"])
    print(f"  matrix shape: {matrix.shape}")

    cfg.paths.models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, cfg.paths.models_dir / "tfidf_incident.joblib")
    sp.save_npz(cfg.paths.models_dir / "incident_matrix.npz", matrix)

    meta_cols = ["number", "short_description_clean", "assignment_group",
                 "business_service", "close_code", "close_notes_clean",
                 "priority", "category"]
    df[meta_cols].to_csv(cfg.paths.models_dir / "incident_meta.csv", index=False)
    print("  saved tfidf_incident.joblib, incident_matrix.npz, incident_meta.csv")


if __name__ == "__main__":
    main()
