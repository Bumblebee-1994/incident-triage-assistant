"""Evaluation: produce metrics tables + matplotlib charts.

Run as a script:
    python -m src.evaluate

Outputs:
    reports/figures/confusion_matrix_ag.png
    reports/figures/confusion_matrix_bs.png  (top-15 classes only, for legibility)
    reports/figures/per_class_f1_ag.png
    reports/figures/per_class_f1_bs.png
    reports/figures/kba_similarity_dist.png
    reports/figures/retrieval_at_k.png
    reports/metrics/retrieval_metrics.json
    reports/metrics/summary.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")  # No display needed; saves directly to disk.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix
from sklearn.metrics.pairwise import cosine_similarity

from src.config import load_config
from src.data_loader import normalize_text


def _load_classification_report(cfg, suffix: str) -> dict:
    path = cfg.paths.metrics_dir / f"classification_report_{suffix}.json"
    return json.loads(path.read_text())


def plot_confusion_matrix_ag(cfg) -> None:
    rep = _load_classification_report(cfg, "ag")
    y_true = np.array(rep["y_test_true"])
    y_pred = np.array(rep["y_test_pred"])
    labels = rep["class_names"]

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))
    fig, ax = plt.subplots(figsize=(7, 5.5))
    disp = ConfusionMatrixDisplay(cm, display_labels=labels)
    disp.plot(ax=ax, cmap="Blues", colorbar=True, values_format="d")
    ax.set_title("Assignment group — confusion matrix (test split)")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    plt.tight_layout()
    out = cfg.paths.figures_dir / "confusion_matrix_ag.png"
    plt.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def plot_confusion_matrix_bs(cfg, top_n: int = 15) -> None:
    rep = _load_classification_report(cfg, "bs")
    y_true = np.array(rep["y_test_true"])
    y_pred = np.array(rep["y_test_pred"])
    labels = rep["class_names"]

    # Pick the top_n classes by support in the test set (legibility).
    counts = np.bincount(y_true, minlength=len(labels))
    top_idx = np.argsort(-counts)[:top_n]
    mask = np.isin(y_true, top_idx)
    y_true_sub = y_true[mask]
    y_pred_sub = y_pred[mask]
    sub_labels = [labels[i] for i in top_idx]

    cm = confusion_matrix(y_true_sub, y_pred_sub, labels=top_idx)
    fig, ax = plt.subplots(figsize=(11, 9))
    disp = ConfusionMatrixDisplay(cm, display_labels=sub_labels)
    disp.plot(ax=ax, cmap="Blues", colorbar=True, values_format="d",
              xticks_rotation=70)
    ax.set_title(f"Business service — confusion matrix (top {top_n} classes)")
    plt.tight_layout()
    out = cfg.paths.figures_dir / "confusion_matrix_bs.png"
    plt.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def plot_per_class_f1(cfg, suffix: str, title: str, top_n: int = 20) -> None:
    rep = _load_classification_report(cfg, suffix)
    test_rep = rep["test"]
    classes = rep["class_names"]
    f1s = [(cls, test_rep[cls]["f1-score"], test_rep[cls]["support"])
           for cls in classes if cls in test_rep]
    f1s.sort(key=lambda x: -x[2])
    f1s = f1s[:top_n]

    names = [c for c, _, _ in f1s]
    scores = [s for _, s, _ in f1s]
    supports = [int(sup) for _, _, sup in f1s]

    fig, ax = plt.subplots(figsize=(9, max(4, 0.35 * len(names))))
    bars = ax.barh(names[::-1], scores[::-1], color="#3B6D11")
    for bar, sup in zip(bars, supports[::-1]):
        ax.text(
            bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
            f"n={sup}", va="center", fontsize=8,
        )
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("F1 score")
    ax.set_title(title)
    plt.tight_layout()
    out = cfg.paths.figures_dir / f"per_class_f1_{suffix}.png"
    plt.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def plot_kba_similarity_dist(cfg) -> None:
    """Distribution of max-cosine-sim to the KB across the test set."""
    inc = pd.read_csv(cfg.paths.processed_dir / "incidents_clean.csv",
                      low_memory=False)
    test_ids = pd.read_csv(cfg.paths.splits_dir / "test.csv")["number"].tolist()
    test_df = inc[inc["number"].isin(test_ids)].copy()

    vec = joblib.load(cfg.paths.models_dir / "tfidf_kb.joblib")
    mat = sp.load_npz(cfg.paths.models_dir / "kb_matrix.npz")
    texts = test_df["text"].fillna("").map(normalize_text).tolist()
    q_mat = vec.transform(texts)
    sims = cosine_similarity(q_mat, mat).max(axis=1)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(sims, bins=40, color="#185FA5", edgecolor="white")
    ax.axvline(cfg.retrieval.kba_threshold, color="#A32D2D", linestyle="--",
               label=f"threshold = {cfg.retrieval.kba_threshold}")
    pct_above = float((sims >= cfg.retrieval.kba_threshold).mean()) * 100
    ax.set_title(f"Max KBA cosine similarity per test incident "
                 f"({pct_above:.1f}% above threshold)")
    ax.set_xlabel("cosine similarity")
    ax.set_ylabel("count of incidents")
    ax.legend()
    plt.tight_layout()
    out = cfg.paths.figures_dir / "kba_similarity_dist.png"
    plt.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")
    return float(pct_above), float(np.median(sims)), float(sims.mean())


def plot_retrieval_at_k(cfg) -> dict:
    """Retrieval@k for similar-incident search.

    For each test incident, we look at the top-k closest TRAIN incidents
    and ask: did at least one of them share the SAME assignment_group?
    """
    inc = pd.read_csv(cfg.paths.processed_dir / "incidents_clean.csv",
                      low_memory=False)
    test_ids = pd.read_csv(cfg.paths.splits_dir / "test.csv")["number"].tolist()
    test_df = inc[inc["number"].isin(test_ids)].reset_index(drop=True).copy()

    vec = joblib.load(cfg.paths.models_dir / "tfidf_incident.joblib")
    mat = sp.load_npz(cfg.paths.models_dir / "incident_matrix.npz")
    meta = pd.read_csv(cfg.paths.models_dir / "incident_meta.csv",
                       low_memory=False)

    texts = test_df["text"].fillna("").map(normalize_text).tolist()
    q_mat = vec.transform(texts)
    sims = cosine_similarity(q_mat, mat)

    ks = [1, 3, 5, 10]
    results = {}
    for k in ks:
        top_idx = np.argsort(-sims, axis=1)[:, :k]
        hit_count = 0
        for i, row_idx in enumerate(top_idx):
            true_ag = test_df.iloc[i]["assignment_group"]
            neighbor_ags = meta.iloc[row_idx]["assignment_group"].tolist()
            if true_ag in neighbor_ags:
                hit_count += 1
        results[k] = hit_count / len(test_df)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(list(results.keys()), list(results.values()),
            marker="o", color="#534AB7", linewidth=2)
    for k, v in results.items():
        ax.annotate(f"{v:.3f}", (k, v),
                    textcoords="offset points", xytext=(0, 8), ha="center")
    ax.set_xticks(ks)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("k (number of neighbors)")
    ax.set_ylabel("recall@k for assignment_group")
    ax.set_title("Similar-incident retrieval recall (test split)")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    out = cfg.paths.figures_dir / "retrieval_at_k.png"
    plt.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")
    return results


def write_summary_csv(cfg) -> None:
    """One-row-per-task overview table."""
    rep_ag = _load_classification_report(cfg, "ag")
    rep_bs = _load_classification_report(cfg, "bs")
    rows = []
    for name, rep in (("assignment_group", rep_ag), ("business_service", rep_bs)):
        for split in ("val", "test"):
            r = rep[split]
            rows.append({
                "task": name,
                "split": split,
                "n_classes": rep["n_classes"],
                "n_samples": rep[f"n_{split}"],
                "accuracy": round(r["accuracy"], 4),
                "macro_f1": round(r["macro avg"]["f1-score"], 4),
                "weighted_f1": round(r["weighted avg"]["f1-score"], 4),
            })
    df = pd.DataFrame(rows)
    out = cfg.paths.metrics_dir / "summary.csv"
    df.to_csv(out, index=False)
    print(f"  wrote {out.name}")
    print(df.to_string(index=False))


def main() -> None:
    cfg = load_config()
    cfg.paths.figures_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.metrics_dir.mkdir(parents=True, exist_ok=True)

    print("Charts:")
    plot_confusion_matrix_ag(cfg)
    plot_confusion_matrix_bs(cfg)
    plot_per_class_f1(cfg, "ag", "Per-class F1 — assignment_group")
    plot_per_class_f1(cfg, "bs", "Per-class F1 — business_service (top 20 by support)")
    pct_above, med, mean = plot_kba_similarity_dist(cfg)
    retrieval = plot_retrieval_at_k(cfg)

    # Persist retrieval metrics.
    with (cfg.paths.metrics_dir / "retrieval_metrics.json").open("w") as f:
        json.dump({
            "kba_pct_above_threshold": pct_above,
            "kba_median_max_similarity": med,
            "kba_mean_max_similarity": mean,
            "kba_threshold": cfg.retrieval.kba_threshold,
            "similar_incident_recall_at_k": retrieval,
        }, f, indent=2)
    print(f"  wrote retrieval_metrics.json")

    print("\nSummary table:")
    write_summary_csv(cfg)


if __name__ == "__main__":
    main()
