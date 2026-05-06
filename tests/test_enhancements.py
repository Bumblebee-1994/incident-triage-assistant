"""Smoke tests for the enhancement overlay.

These tests verify only structural / import-level correctness — they do
NOT require the trained models. CI can run them in <2 seconds.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_overlay_files_exist():
    """All expected overlay files are in place."""
    must_exist = [
        ".github/copilot-instructions.md",
        ".github/workflows/triage-issue.yml",
        ".github/ISSUE_TEMPLATE/incident.yml",
        ".devcontainer/devcontainer.json",
        ".devcontainer/post-create.sh",
        "scripts/__init__.py",
        "scripts/triage_cli.py",
        "scripts/mcp_server.py",
        "scripts/triage_issue_body.py",
        "BUSINESS_CASE.md",
        "COPILOT_USAGE.md",
        "docs/ENHANCEMENTS.md",
    ]
    missing = [p for p in must_exist if not (PROJECT_ROOT / p).exists()]
    assert not missing, f"Missing overlay files: {missing}"


def test_devcontainer_json_is_valid():
    """devcontainer.json must be valid JSON with the right shape."""
    path = PROJECT_ROOT / ".devcontainer" / "devcontainer.json"
    data = json.loads(path.read_text())
    assert "image" in data
    assert "GitHub.copilot" in data["customizations"]["vscode"]["extensions"]
    assert 5000 in data["forwardPorts"]


def test_overlay_scripts_compile():
    """All overlay Python scripts import without syntax errors."""
    # We don't actually run their main() — that requires trained models.
    # We just verify the module-level code is parseable and importable.
    for module in ("scripts.triage_issue_body", "scripts.mcp_server"):
        importlib.import_module(module)


def test_mcp_server_handles_initialize():
    """The MCP server's initialize handler returns the right shape."""
    from scripts.mcp_server import _handle_request, PROTOCOL_VERSION
    req = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                   "clientInfo": {"name": "test", "version": "0"}},
    }
    resp = _handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert "tools" in resp["result"]["capabilities"]
    assert resp["result"]["serverInfo"]["name"] == "incident-triage"


def test_mcp_server_lists_tools():
    """The MCP server exposes both tools."""
    from scripts.mcp_server import _handle_request
    resp = _handle_request({"jsonrpc": "2.0", "id": 2,
                            "method": "tools/list", "params": {}})
    tool_names = {t["name"] for t in resp["result"]["tools"]}
    assert "triage_incident" in tool_names
    assert "list_sample_incidents" in tool_names


def test_triage_issue_body_stub_path():
    """When models aren't present, the helper emits a graceful stub."""
    from scripts import triage_issue_body
    # The STUB_RESPONSE must be a complete shape the workflow can consume.
    stub = triage_issue_body.STUB_RESPONSE
    assert "predicted_group" in stub
    assert "comment_markdown" in stub
    assert stub["predicted_group"] == ""  # signals "no label" to the workflow
    assert "Triage skipped" in stub["comment_markdown"]


def test_triage_cli_argparse():
    """The CLI's argparse setup is valid and exposes the right flags."""
    # We import the module and verify main() is callable. Running it
    # without args would drop into the REPL, so we just check structure.
    from scripts import triage_cli
    assert hasattr(triage_cli, "main")
    assert hasattr(triage_cli, "TriageAgent")
    assert hasattr(triage_cli, "run_repl")


def test_copilot_instructions_has_required_sections():
    """The Copilot instructions file mentions our key project rules."""
    text = (PROJECT_ROOT / ".github" / "copilot-instructions.md").read_text()
    # Must mention the no-LLM rule.
    assert "Never introduce dependencies on hosted LLMs" in text
    # Must mention the no-fabrication rule.
    assert "Never invent KBA references" in text
    # Must mention the non-destructive runbook rule.
    assert "non-destructive" in text


def test_triage_workflow_yaml_is_well_formed():
    """The triage workflow YAML parses and has expected structure."""
    import yaml
    path = PROJECT_ROOT / ".github" / "workflows" / "triage-issue.yml"
    data = yaml.safe_load(path.read_text())
    # YAML's `on:` key is parsed as Python's `True` because YAML 1.1
    # — accept either.
    on_key = data.get("on") or data.get(True)
    assert on_key is not None, "Workflow has no 'on:' trigger"
    assert "issues" in on_key
    assert "triage" in data["jobs"]
    # Permissions are at the workflow level (one of two valid placements).
    assert data.get("permissions", {}).get("issues") == "write"
