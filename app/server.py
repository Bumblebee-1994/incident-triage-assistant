"""Flask server for the live demo dashboard.

Endpoints:
    GET  /                  -> the dashboard UI (templates/index.html)
    GET  /sample_incidents  -> a list of test-split incidents to populate the
                                "pick an incident" dropdown in the UI.
    POST /analyze           -> accepts JSON body with EITHER:
                                {"incident_number": "INC00..."}
                                OR
                                {"short_description": "...", "description": "..."}
                               Returns the four rendered artifacts + raw evidence.
    GET  /reports/<path>    -> serves files from the reports/ folder (figures,
                                metrics) so the dashboard can show charts.

Run:
    python -m app.server
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python -m app.server` and `python app/server.py` alike.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_from_directory

from src.config import load_config
from src.generate import analyze_incident

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)

CFG = load_config()


def _load_test_incidents_df() -> pd.DataFrame:
    """Cache test-split incidents in memory for the dropdown."""
    inc = pd.read_csv(CFG.paths.processed_dir / "incidents_clean.csv",
                      low_memory=False)
    test_ids = pd.read_csv(CFG.paths.splits_dir / "test.csv")["number"].tolist()
    return inc[inc["number"].isin(test_ids)].reset_index(drop=True)


_TEST_INC_DF = None


def _test_incidents() -> pd.DataFrame:
    global _TEST_INC_DF
    if _TEST_INC_DF is None:
        _TEST_INC_DF = _load_test_incidents_df()
    return _TEST_INC_DF


@app.route("/")
def index():
    return render_template("index.html",
                           kba_threshold=CFG.retrieval.kba_threshold)


@app.route("/sample_incidents")
def sample_incidents():
    """Return a small list of test incidents for the demo dropdown."""
    df = _test_incidents().head(50)
    items = [
        {
            "number": str(row["number"]),
            "short_description": (str(row["short_description"]) or "")[:120],
            "priority": str(row.get("priority", "")),
        }
        for _, row in df.iterrows()
    ]
    return jsonify(items)


@app.route("/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}

    if payload.get("incident_number"):
        inc_num = str(payload["incident_number"]).strip()
        df = _test_incidents()
        match = df[df["number"] == inc_num]
        if match.empty:
            return jsonify({"error": f"Incident {inc_num} not in test set."}), 404
        incident = match.iloc[0].to_dict()
    else:
        # Free-form text path.
        short = (payload.get("short_description") or "").strip()
        long_ = (payload.get("description") or "").strip()
        if not short and not long_:
            return jsonify({"error": "Provide incident_number or text."}), 400
        incident = {
            "number": "AD-HOC",
            "short_description": short,
            "description": long_,
            "priority": payload.get("priority", "3 - Moderate"),
            "caller_id": payload.get("caller_id", ""),
            "sys_created_on": "",
            "resolved_at": "",
        }

    result = analyze_incident(incident)
    # Add a couple of UI-friendly summary fields.
    result["incident_meta"] = {
        "number": incident.get("number"),
        "short_description": incident.get("short_description"),
        "priority": incident.get("priority"),
    }
    return jsonify(result)


@app.route("/reports/<path:relpath>")
def reports(relpath: str):
    """Serve files from reports/ so the page can <img src="..."> the charts."""
    return send_from_directory(CFG.paths.reports_dir, relpath)


def main() -> None:
    app.run(
        host=CFG.flask.host,
        port=CFG.flask.port,
        debug=CFG.flask.debug,
    )


if __name__ == "__main__":
    main()
