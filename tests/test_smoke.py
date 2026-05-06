"""Minimal smoke tests — run by CI on every push.

These tests verify the moving parts work, without requiring the full
trained models. They are designed to run in under 10 seconds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_config_loads():
    from src.config import load_config
    cfg = load_config()
    assert cfg.paths.incidents_xlsx.name == "incident_dump.xlsx"
    assert cfg.split.train_ratio + cfg.split.val_ratio + cfg.split.test_ratio == pytest.approx(1.0)
    assert 0 < cfg.retrieval.kba_threshold < 1


def test_html_cleaner_handles_edge_cases():
    from src.data_loader import clean_html, normalize_text
    assert clean_html(None) == ""
    assert clean_html("") == ""
    assert clean_html("plain text") == "plain text"
    assert clean_html("<p>hello <b>world</b></p>") == "hello world"
    assert clean_html("Item&nbsp;A") == "Item A"
    # Non-string input should not crash.
    import pandas as pd
    assert clean_html(pd.NA) == ""
    assert clean_html(float("nan")) == ""
    # normalize_text lowercases and collapses whitespace.
    assert normalize_text("  Hello   World  ") == "hello world"


def test_jinja_templates_render_without_errors():
    """Render every template with a minimal fake context."""
    from src.generate import _make_jinja_env
    env = _make_jinja_env()
    fake_ctx = {
        "incident": {
            "number": "INC0000001",
            "short_description": "Test ticket",
            "description": "Test description",
            "priority": "3 - Moderate",
            "sys_created_on": "2025-01-01",
            "resolved_at": "",
            "caller_id": "Jane Doe",
            "caller_first_name": "Jane",
        },
        "predicted_group": "TEAM.X",
        "predicted_group_top3": [
            {"label": "TEAM.X", "prob": 0.9},
            {"label": "TEAM.Y", "prob": 0.07},
            {"label": "TEAM.Z", "prob": 0.03},
        ],
        "predicted_service_top3": [
            {"label": "Service A", "prob": 0.5},
            {"label": "Service B", "prob": 0.3},
            {"label": "Service C", "prob": 0.2},
        ],
        "kba_matches": [],
        "kba_threshold": 0.25,
        "similar_incidents": [
            {
                "number": "INC0000099",
                "short_description": "Similar past issue",
                "assignment_group": "TEAM.X",
                "business_service": "Service A",
                "close_code": "Solution provided",
                "close_notes_excerpt": "Did the thing.",
                "score": 0.42,
            }
        ],
    }
    for name in ("user_summary.md.j2", "it_summary.md.j2",
                 "runbook.md.j2", "postmortem.md.j2"):
        out = env.get_template(name).render(**fake_ctx)
        assert "INC0000001" in out
        assert len(out) > 100, f"{name} produced too short an output"


def test_no_kba_match_path_in_user_summary():
    """When there are no KBA matches, the user summary must say so explicitly."""
    from src.generate import _make_jinja_env
    env = _make_jinja_env()
    out = env.get_template("user_summary.md.j2").render(
        incident={
            "number": "INC0000002",
            "short_description": "Test",
            "description": "",
            "priority": "3",
            "caller_id": "",
            "caller_first_name": "",
            "sys_created_on": "",
            "resolved_at": "",
        },
        predicted_group="TEAM.X",
        predicted_group_top3=[{"label": "TEAM.X", "prob": 0.9}],
        predicted_service_top3=[{"label": "Service A", "prob": 0.5}],
        kba_matches=[],
        kba_threshold=0.25,
        similar_incidents=[],
    )
    # Honest "no match" wording, NOT a fabricated suggestion.
    assert "have not found a known self-help guide" in out.lower()
