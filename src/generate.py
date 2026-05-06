"""Render the four artifacts (user/IT/runbook/postmortem) for an incident.

Two entry points:
    1. CLI:        python -m src.generate --num 5
       Picks N random incidents from the test split, renders all four
       artifacts for each, and writes them to reports/samples/.
    2. Library:    analyze_incident(incident_dict) -> dict[str, str]
       Used by the Flask app.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import load_config
from src.retrieve import (
    predict_assignment_group,
    predict_business_service,
    retrieve_kbas,
    retrieve_similar_incidents,
)


def _make_jinja_env() -> Environment:
    """Build a Jinja2 environment that loads templates from src/prompts/."""
    template_dir = Path(__file__).parent / "prompts"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(disabled_extensions=("md", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def analyze_incident(incident: dict[str, Any]) -> dict[str, Any]:
    """Run all retrieval + classification + templating for one incident.

    `incident` must have keys:
        number, short_description, description, priority,
        sys_created_on (optional), resolved_at (optional),
        caller_id (optional)
    Returns a dict with the four rendered markdown strings plus metadata.
    """
    cfg = load_config()
    env = _make_jinja_env()

    # Build the query text the same way training does.
    query = " . ".join(filter(None, [
        str(incident.get("short_description", "") or ""),
        str(incident.get("description", "") or ""),
    ])).strip()

    # Predictions.
    ag = predict_assignment_group(query)
    bs = predict_business_service(query)

    # Retrieval.
    kba_matches = [m.to_dict() for m in retrieve_kbas(query)]
    sim_incidents = [s.to_dict() for s in retrieve_similar_incidents(query)]

    # Caller first name (best effort, just for the user template).
    caller = str(incident.get("caller_id", "") or "")
    caller_first_name = caller.split()[0] if caller else ""

    template_ctx = {
        "incident": {
            **incident,
            "caller_first_name": caller_first_name,
            "short_description": str(incident.get("short_description", "") or ""),
            "description": str(incident.get("description", "") or ""),
            "priority": str(incident.get("priority", "") or "Unknown"),
            "sys_created_on": str(incident.get("sys_created_on", "") or "—"),
            "resolved_at": str(incident.get("resolved_at", "") or ""),
            "caller_id": caller or "—",
        },
        "predicted_group": ag["top1"],
        "predicted_group_top3": ag["top3"],
        "predicted_service_top3": bs["top3"],
        "kba_matches": kba_matches,
        "kba_threshold": cfg.retrieval.kba_threshold,
        "similar_incidents": sim_incidents,
    }

    rendered = {
        "user_summary": env.get_template("user_summary.md.j2").render(**template_ctx),
        "it_summary": env.get_template("it_summary.md.j2").render(**template_ctx),
        "runbook": env.get_template("runbook.md.j2").render(**template_ctx),
        "postmortem": env.get_template("postmortem.md.j2").render(**template_ctx),
    }

    return {
        "rendered": rendered,
        "predictions": {"assignment_group": ag, "business_service": bs},
        "kba_matches": kba_matches,
        "similar_incidents": sim_incidents,
        "kba_threshold": cfg.retrieval.kba_threshold,
    }


def write_sample_outputs(num: int = 5, seed: int = 42) -> list[str]:
    """Pick N test-split incidents and write all four .md files for each.

    Sampling strategy: deliberately pick a mix of (a) incidents whose
    closest KBA is HIGH similarity, and (b) random ones. This guarantees
    the demo shows both "KBA found" and "no strong match" cases.
    """
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    from src.data_loader import normalize_text
    from src.retrieve import _load_kb_index

    cfg = load_config()
    inc = pd.read_csv(cfg.paths.processed_dir / "incidents_clean.csv",
                      low_memory=False)
    test_ids = pd.read_csv(cfg.paths.splits_dir / "test.csv")["number"].tolist()
    test_df = inc[inc["number"].isin(test_ids)].reset_index(drop=True)

    # Compute max KB similarity for ranking.
    vec, mat, _ = _load_kb_index()
    texts = test_df["text"].fillna("").map(normalize_text).tolist()
    q_mat = vec.transform(texts)
    sims = cosine_similarity(q_mat, mat).max(axis=1)
    test_df = test_df.assign(max_kb_sim=sims)

    # Half from the top (KBA-rich), half random (mixed).
    n_top = max(1, num // 2)
    n_random = num - n_top
    top_picks = test_df.nlargest(n_top, "max_kb_sim")
    rng = np.random.default_rng(seed)
    pool = test_df.drop(top_picks.index)
    rand_picks = pool.iloc[rng.choice(len(pool), size=n_random, replace=False)]
    sample = pd.concat([top_picks, rand_picks], ignore_index=True)

    cfg.paths.samples_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for _, row in sample.iterrows():
        incident = row.to_dict()
        result = analyze_incident(incident)
        for key, body in result["rendered"].items():
            out_path = cfg.paths.samples_dir / f"{row['number']}_{key}.md"
            out_path.write_text(body, encoding="utf-8")
            written.append(str(out_path.name))
        print(f"  {row['number']}  max_kb_sim={row['max_kb_sim']:.3f}  "
              f"KBA matches: {len(result['kba_matches'])}  "
              f"AG: {result['predictions']['assignment_group']['top1']}")
    print(f"\nWrote {len(written)} files to {cfg.paths.samples_dir}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample artifacts.")
    parser.add_argument("--num", type=int, default=5,
                        help="Number of test incidents to render")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    write_sample_outputs(num=args.num, seed=args.seed)


if __name__ == "__main__":
    main()
