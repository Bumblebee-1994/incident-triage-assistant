"""Build a TF-IDF index over Knowledge Base Articles for retrieval.

Run as a script:
    python -m src.build_kb_index

Outputs:
    models/tfidf_kb.joblib       (fitted TfidfVectorizer)
    models/kb_matrix.npz         (sparse KB-vector matrix)
    models/kb_meta.csv           (kb_number + short_description, in row order)
"""
from __future__ import annotations

import joblib
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import load_config


def main() -> None:
    cfg = load_config()

    print("Loading cleaned KBAs...")
    kb = pd.read_csv(cfg.paths.processed_dir / "kb_clean.csv", low_memory=False)
    kb["text"] = kb["text"].fillna("").astype(str)
    print(f"  KBA rows: {len(kb):,}")

    print("Fitting TF-IDF on KBA text...")
    vectorizer = TfidfVectorizer(
        max_features=cfg.tfidf.max_features,
        ngram_range=tuple(cfg.tfidf.ngram_range),
        min_df=cfg.tfidf.min_df,
        max_df=cfg.tfidf.max_df,
        sublinear_tf=cfg.tfidf.sublinear_tf,
        strip_accents=cfg.tfidf.strip_accents,
        lowercase=True,
    )
    matrix = vectorizer.fit_transform(kb["text"])
    print(f"  matrix shape: {matrix.shape}  (KBs x vocab)")

    cfg.paths.models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, cfg.paths.models_dir / "tfidf_kb.joblib")
    sp.save_npz(cfg.paths.models_dir / "kb_matrix.npz", matrix)

    # Save metadata so retrieval can map row index -> kb_number + title.
    meta_cols = ["kb_number", "short_description", "introduction",
                 "instructions", "article_body"]
    kb[meta_cols].to_csv(cfg.paths.models_dir / "kb_meta.csv", index=False)
    print(f"  saved tfidf_kb.joblib, kb_matrix.npz, kb_meta.csv")


if __name__ == "__main__":
    main()
