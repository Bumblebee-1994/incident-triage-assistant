"""Preprocess incidents + KBAs and produce reproducible train/val/test splits.

Run as a script:
    python -m src.preprocess

Outputs:
    data/processed/incidents_clean.csv
    data/processed/kb_clean.csv
    data/splits/train.csv  (just incident 'number' column)
    data/splits/val.csv
    data/splits/test.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import load_config
from src.data_loader import load_incidents, load_kbas


def _filter_rare_classes(df: pd.DataFrame, col: str, min_samples: int) -> pd.DataFrame:
    """Drop rows whose label appears fewer than `min_samples` times.

    Stratified splitting in scikit-learn requires each class to have at
    least `n_splits` samples. We use a stricter minimum so the test set
    always contains a usable count per class.
    """
    counts = df[col].value_counts()
    keep = counts[counts >= min_samples].index
    return df[df[col].isin(keep)].reset_index(drop=True)


def make_splits(
    df: pd.DataFrame,
    label_col: str,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified train/val/test split using two sequential train_test_splits."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Split ratios must sum to 1"

    # First carve off the test set.
    df_train_val, df_test = train_test_split(
        df,
        test_size=test_ratio,
        random_state=seed,
        stratify=df[label_col],
    )
    # Then split the remainder into train/val.
    val_relative = val_ratio / (train_ratio + val_ratio)
    df_train, df_val = train_test_split(
        df_train_val,
        test_size=val_relative,
        random_state=seed,
        stratify=df_train_val[label_col],
    )
    return (
        df_train.reset_index(drop=True),
        df_val.reset_index(drop=True),
        df_test.reset_index(drop=True),
    )


def main() -> None:
    cfg = load_config()

    print("Loading raw data...")
    inc = load_incidents(cfg.paths.incidents_xlsx)
    kb = load_kbas(cfg.paths.kb_xlsx)
    print(f"  incidents: {len(inc):,}   kbas: {len(kb):,}")

    # Save cleaned full corpus before filtering — useful for retrieval.
    cfg.paths.processed_dir.mkdir(parents=True, exist_ok=True)
    inc.to_csv(cfg.paths.processed_dir / "incidents_clean.csv", index=False)
    kb.to_csv(cfg.paths.processed_dir / "kb_clean.csv", index=False)
    print(f"  wrote incidents_clean.csv and kb_clean.csv")

    # Stratify on assignment_group (primary classifier label).
    print("\nFiltering rare assignment_group classes...")
    inc_filt = _filter_rare_classes(
        inc, "assignment_group", cfg.split.min_class_samples
    )
    print(f"  rows kept: {len(inc_filt):,} / {len(inc):,}")
    print(f"  assignment_group classes: {inc_filt['assignment_group'].nunique()}")

    # Some business_service values may also be rare, but we don't drop incidents
    # for that — we will filter labels at training time for the BS classifier.

    # Splits.
    print("\nMaking stratified train/val/test splits...")
    train, val, test = make_splits(
        inc_filt,
        label_col="assignment_group",
        train_ratio=cfg.split.train_ratio,
        val_ratio=cfg.split.val_ratio,
        test_ratio=cfg.split.test_ratio,
        seed=cfg.split.random_seed,
    )
    print(f"  train: {len(train):,}   val: {len(val):,}   test: {len(test):,}")

    cfg.paths.splits_dir.mkdir(parents=True, exist_ok=True)
    train[["number"]].to_csv(cfg.paths.splits_dir / "train.csv", index=False)
    val[["number"]].to_csv(cfg.paths.splits_dir / "val.csv", index=False)
    test[["number"]].to_csv(cfg.paths.splits_dir / "test.csv", index=False)
    print(f"  wrote train.csv / val.csv / test.csv")

    # Print class balance for transparency in the demo.
    print("\nClass balance on training set (assignment_group):")
    print(train["assignment_group"].value_counts().to_string())


if __name__ == "__main__":
    main()
