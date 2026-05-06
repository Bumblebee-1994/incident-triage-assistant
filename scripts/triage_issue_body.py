"""Triage a GitHub issue body and emit a JSON result + a markdown comment.

Used by `.github/workflows/triage-issue.yml`. Designed to fail GRACEFULLY
when models are not built yet — emits a stub response so the workflow
still posts a useful comment.

Run as:
    python scripts/triage_issue_body.py \
        --title "Cannot login to SAP" \
        --body  "Account locked, error S001..." \
        --output /tmp/triage.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is importable when this script is invoked directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


STUB_RESPONSE = {
    "predicted_group": "",
    "comment_markdown": (
        "### 🤖 Auto-triage result\n\n"
        "_Triage skipped — trained models are not available in this run. "
        "Add `data/raw/*.xlsx` and re-run the workflow, or trigger it via "
        "`workflow_dispatch`._"
    ),
}


def _models_present() -> bool:
    models_dir = PROJECT_ROOT / "models"
    needed = [
        "tfidf_text_ag.joblib",
        "clf_assignment_group.joblib",
        "label_encoder_ag.joblib",
        "tfidf_kb.joblib",
        "kb_matrix.npz",
        "kb_meta.csv",
        "tfidf_incident.joblib",
        "incident_matrix.npz",
        "incident_meta.csv",
    ]
    return all((models_dir / f).exists() for f in needed)


def _build_comment(result: dict, title: str) -> str:
    """Compose a clean GitHub-flavoured markdown comment from the triage result."""
    preds = result["predictions"]
    ag = preds["assignment_group"]
    bs = preds["business_service"]
    kbas = result.get("kba_matches") or []
    sims = result.get("similar_incidents") or []
    threshold = result.get("kba_threshold", 0.25)

    lines = [
        "### 🤖 Auto-triage result",
        "",
        f"**Title:** {title or '_(no title)_'}",
        "",
        "#### Predicted routing",
        "",
        "| Field | Top prediction | Confidence | 2nd | 3rd |",
        "| --- | --- | --- | --- | --- |",
        f"| Assignment group | `{ag['top1']}` | {ag['top1_prob']*100:.0f}% | "
        f"`{ag['top3'][1]['label']}` ({ag['top3'][1]['prob']*100:.0f}%) | "
        f"`{ag['top3'][2]['label']}` ({ag['top3'][2]['prob']*100:.0f}%) |",
        f"| Business service | `{bs['top1']}` | {bs['top1_prob']*100:.0f}% | "
        f"`{bs['top3'][1]['label']}` ({bs['top3'][1]['prob']*100:.0f}%) | "
        f"`{bs['top3'][2]['label']}` ({bs['top3'][2]['prob']*100:.0f}%) |",
        "",
    ]

    lines.append("#### KBA recommendations")
    if kbas:
        for k in kbas[:3]:
            lines.append(f"- **{k['kb_number']}** ({k['score']:.2f}) — {k['short_description']}")
    else:
        lines.append(f"_No KBA passed the {threshold:.2f} similarity threshold — "
                     f"do not force a recommendation._")
    lines.append("")

    lines.append("#### Top similar historical incidents")
    if sims:
        for s in sims[:3]:
            lines.append(
                f"- **{s['number']}** ({s['score']:.2f}) — `{s['close_code']}` — "
                f"{s['short_description'][:100]}"
            )
    else:
        lines.append("_No similar incidents found._")
    lines.append("")

    lines.append("---")
    lines.append("_Generated automatically by the auto-triage workflow. "
                 "Edit `.github/workflows/triage-issue.yml` to tune behavior._")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="", help="Issue title")
    parser.add_argument("--body", default="", help="Issue body (description)")
    parser.add_argument("--output", required=True, help="Path to JSON output file")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not _models_present():
        out_path.write_text(json.dumps(STUB_RESPONSE), encoding="utf-8")
        print("Stub response written (models not present).")
        return

    # Lazy import — only after we know models exist.
    from src.generate import analyze_incident

    incident = {
        "number": "GH-ISSUE",
        "short_description": args.title,
        "description": args.body,
        "priority": "3 - Moderate",
        "caller_id": "",
        "sys_created_on": "",
        "resolved_at": "",
    }
    result = analyze_incident(incident)

    payload = {
        "predicted_group": result["predictions"]["assignment_group"]["top1"],
        "comment_markdown": _build_comment(result, args.title),
    }
    out_path.write_text(json.dumps(payload), encoding="utf-8")
    print(f"Triage result written to {out_path}")


if __name__ == "__main__":
    main()
