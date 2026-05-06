"""Train two text classifiers using a shared TF-IDF pipeline.

    1. assignment_group  — 3 classes, severely imbalanced
    2. business_service  — up to 90 classes, fewer rows per class

Both use:
    TfidfVectorizer(word 1-2grams) -> LogisticRegression(class_weight=balanced)

Run as a script:
    python -m src.train_classifier
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder

from src.config import load_config


def _load_split(cfg, name: str) -> pd.DataFrame:
    """Load incident rows for a given split (train/val/test)."""
    inc = pd.read_csv(cfg.paths.processed_dir / "incidents_clean.csv",
                      low_memory=False)
    ids = pd.read_csv(cfg.paths.splits_dir / f"{name}.csv")["number"].tolist()
    df = inc[inc["number"].isin(ids)].reset_index(drop=True)
    df["text"] = df["text"].fillna("").astype(str)
    return df


def _filter_to_known_labels(
    df: pd.DataFrame, label_col: str, allowed: set[str]
) -> pd.DataFrame:
    """Keep only rows whose label is in `allowed`."""
    return df[df[label_col].isin(allowed)].reset_index(drop=True)


def _train_one(
    label_col: str,
    cfg,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict:
    """Train one classifier end-to-end. Returns metrics dict."""
    print(f"\n{'='*60}\n  Training classifier: {label_col}\n{'='*60}")

    # Restrict to classes that have at least min_class_samples in train.
    counts = train_df[label_col].value_counts()
    allowed = set(counts[counts >= cfg.split.min_class_samples].index)
    if "" in allowed:
        allowed.discard("")
    print(f"  Classes kept (>= {cfg.split.min_class_samples} train samples): "
          f"{len(allowed)}")

    train_df = _filter_to_known_labels(train_df, label_col, allowed)
    val_df = _filter_to_known_labels(val_df, label_col, allowed)
    test_df = _filter_to_known_labels(test_df, label_col, allowed)
    print(f"  Train: {len(train_df):,}  Val: {len(val_df):,}  Test: {len(test_df):,}")

    # Vectorizer.
    vectorizer = TfidfVectorizer(
        max_features=cfg.tfidf.max_features,
        ngram_range=tuple(cfg.tfidf.ngram_range),
        min_df=cfg.tfidf.min_df,
        max_df=cfg.tfidf.max_df,
        sublinear_tf=cfg.tfidf.sublinear_tf,
        strip_accents=cfg.tfidf.strip_accents,
        lowercase=True,
    )
    X_train = vectorizer.fit_transform(train_df["text"])
    X_val = vectorizer.transform(val_df["text"])
    X_test = vectorizer.transform(test_df["text"])

    # Label encoder.
    le = LabelEncoder()
    y_train = le.fit_transform(train_df[label_col])
    y_val = le.transform(val_df[label_col])
    y_test = le.transform(test_df[label_col])

    # Classifier.
    clf = LogisticRegression(
        C=cfg.classifier.C,
        max_iter=cfg.classifier.max_iter,
        class_weight=cfg.classifier.class_weight,
        solver="lbfgs",
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # Evaluate.
    val_pred = clf.predict(X_val)
    test_pred = clf.predict(X_test)

    val_report = classification_report(
        y_val, val_pred,
        labels=np.arange(len(le.classes_)),
        target_names=le.classes_,
        output_dict=True,
        zero_division=0,
    )
    test_report = classification_report(
        y_test, test_pred,
        labels=np.arange(len(le.classes_)),
        target_names=le.classes_,
        output_dict=True,
        zero_division=0,
    )

    print(f"\n  Val   accuracy: {val_report['accuracy']:.4f}  "
          f"macro-F1: {val_report['macro avg']['f1-score']:.4f}")
    print(f"  Test  accuracy: {test_report['accuracy']:.4f}  "
          f"macro-F1: {test_report['macro avg']['f1-score']:.4f}")

    # Save artifacts.
    suffix = "ag" if label_col == "assignment_group" else "bs"
    cfg.paths.models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, cfg.paths.models_dir / f"tfidf_text_{suffix}.joblib")
    joblib.dump(clf, cfg.paths.models_dir / f"clf_{label_col}.joblib")
    joblib.dump(le, cfg.paths.models_dir / f"label_encoder_{suffix}.joblib")

    # Save reports.
    cfg.paths.metrics_dir.mkdir(parents=True, exist_ok=True)
    with (cfg.paths.metrics_dir / f"classification_report_{suffix}.json").open("w") as f:
        json.dump({
            "label_column": label_col,
            "n_classes": len(le.classes_),
            "n_train": len(train_df),
            "n_val": len(val_df),
            "n_test": len(test_df),
            "val": val_report,
            "test": test_report,
            "y_test_true": y_test.tolist(),
            "y_test_pred": test_pred.tolist(),
            "class_names": le.classes_.tolist(),
        }, f, indent=2)
    print(f"  Saved model + metrics for {label_col}")

    return {"val": val_report, "test": test_report}


def main() -> None:
    cfg = load_config()

    train_df = _load_split(cfg, "train")
    val_df = _load_split(cfg, "val")
    test_df = _load_split(cfg, "test")
    print(f"Loaded splits: {len(train_df):,} / {len(val_df):,} / {len(test_df):,}")

    _train_one("assignment_group", cfg, train_df, val_df, test_df)
    _train_one("business_service", cfg, train_df, val_df, test_df)
    print("\nDone.")


if __name__ == "__main__":
    main()
