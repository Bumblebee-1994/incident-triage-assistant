"""Model Context Protocol (MCP) server wrapping the triage engine.

This makes the triage assistant callable as a tool from any MCP-aware
client — Claude Desktop, Continue, the GitHub Copilot agent, etc.

The protocol implementation here is **stdio JSON-RPC 2.0 with the MCP
2024-11-05 message envelope**, written from scratch with **zero extra
dependencies** so it works in any environment that already has this
project's `requirements.txt` installed. No `mcp`/`fastmcp` package needed.

Run:
    python -m scripts.mcp_server

Then add to e.g. Claude Desktop's `claude_desktop_config.json`:
    {
      "mcpServers": {
        "incident-triage": {
          "command": "python",
          "args": ["-m", "scripts.mcp_server"],
          "cwd": "/absolute/path/to/incident-triage-assistant-final"
        }
      }
    }

Once added, the client sees a tool named `triage_incident` that accepts
a short_description and (optional) description, and returns the same
structure the Flask /analyze endpoint returns.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

# Project root must be on sys.path so `from src...` works when this is
# invoked as a stdio subprocess from outside VS Code.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# --- MCP protocol primitives ------------------------------------------------
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "incident-triage"
SERVER_VERSION = "0.1.0"


def _read_message() -> dict | None:
    """Read one JSON-RPC line-delimited message from stdin.

    MCP-over-stdio uses newline-delimited JSON (NOT Content-Length headers
    — that's the LSP variant). One JSON object per line.
    """
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        _log(f"bad JSON from client: {e}")
        return None


def _write_message(payload: dict) -> None:
    """Write one JSON-RPC line-delimited message to stdout."""
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _log(msg: str) -> None:
    """Diagnostic log to stderr — stdout is reserved for protocol traffic."""
    sys.stderr.write(f"[mcp-triage] {msg}\n")
    sys.stderr.flush()


def _ok_response(req_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error_response(req_id: Any, code: int, message: str, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


# --- Tool definitions -------------------------------------------------------
TOOLS = [
    {
        "name": "triage_incident",
        "description": (
            "Triage a ServiceNow-style incident. Given a short description "
            "(and optionally a longer description), returns predicted "
            "assignment group, predicted business service, KBA matches "
            "above the confidence threshold, top-5 similar historical "
            "incidents, and four pre-rendered markdown artifacts (user "
            "summary, IT summary, runbook, draft postmortem). Nothing is "
            "hallucinated — every field is grounded in the indexed corpus."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "short_description": {
                    "type": "string",
                    "description": "One-line summary of the incident.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional longer description with details, error codes, etc.",
                },
                "priority": {
                    "type": "string",
                    "description": "Optional priority label, e.g. '2 - High'.",
                    "default": "3 - Moderate",
                },
            },
            "required": ["short_description"],
        },
    },
    {
        "name": "list_sample_incidents",
        "description": (
            "Return a small list of test-split incident numbers and their "
            "short descriptions, so the caller can pick a real one to "
            "triage instead of typing a fake one."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "How many incidents to return (max 50).",
                    "default": 10,
                }
            },
        },
    },
]


# --- Tool implementations ---------------------------------------------------


def _run_triage(args: dict) -> dict:
    """Call the existing analyze_incident() and shape the response."""
    from src.generate import analyze_incident  # lazy import: heavy

    short = (args.get("short_description") or "").strip()
    long_ = (args.get("description") or "").strip()
    if not short and not long_:
        raise ValueError("short_description or description must be provided")

    incident = {
        "number": "MCP-CALL",
        "short_description": short,
        "description": long_,
        "priority": args.get("priority", "3 - Moderate"),
        "caller_id": "",
        "sys_created_on": "",
        "resolved_at": "",
    }
    result = analyze_incident(incident)

    # Compose a one-shot text block that's nice to read directly in chat.
    rendered = result["rendered"]
    preds = result["predictions"]
    text_blob = (
        "## Predicted routing\n"
        f"- Assignment group: `{preds['assignment_group']['top1']}` "
        f"({preds['assignment_group']['top1_prob']*100:.0f}% confidence)\n"
        f"- Business service: `{preds['business_service']['top1']}` "
        f"({preds['business_service']['top1_prob']*100:.0f}% confidence)\n\n"
        + rendered["it_summary"]
    )

    return {
        "predictions": preds,
        "kba_matches": result["kba_matches"],
        "similar_incidents": result["similar_incidents"],
        "kba_threshold": result["kba_threshold"],
        "rendered": rendered,
        "summary_text": text_blob,
    }


def _list_samples(args: dict) -> dict:
    """Return a small list of test-split incidents from the cleaned data."""
    import pandas as pd
    from src.config import load_config

    cfg = load_config()
    limit = max(1, min(50, int(args.get("limit", 10))))

    inc_path = cfg.paths.processed_dir / "incidents_clean.csv"
    splits_path = cfg.paths.splits_dir / "test.csv"
    if not inc_path.exists() or not splits_path.exists():
        return {
            "items": [],
            "note": (
                "Pipeline has not been run yet. Run "
                "`python -m src.pipeline all` first."
            ),
        }

    inc = pd.read_csv(inc_path, low_memory=False)
    test_ids = pd.read_csv(splits_path)["number"].tolist()
    rows = inc[inc["number"].isin(test_ids)].head(limit)

    items = [
        {
            "number": str(r["number"]),
            "short_description": str(r.get("short_description", ""))[:140],
            "priority": str(r.get("priority", "")),
        }
        for _, r in rows.iterrows()
    ]
    return {"items": items}


TOOL_HANDLERS = {
    "triage_incident": _run_triage,
    "list_sample_incidents": _list_samples,
}


# --- JSON-RPC dispatcher ----------------------------------------------------


def _handle_request(req: dict) -> dict | None:
    """Route an incoming JSON-RPC request to the right MCP handler."""
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    # Notifications (no id) get no response.
    is_notification = "id" not in req

    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
            return _ok_response(req_id, result)

        if method == "notifications/initialized":
            return None  # spec: no response

        if method == "tools/list":
            return _ok_response(req_id, {"tools": TOOLS})

        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            handler = TOOL_HANDLERS.get(name)
            if handler is None:
                return _error_response(req_id, -32601, f"Unknown tool: {name}")
            try:
                result = handler(args)
            except Exception as exc:
                _log(f"tool {name} raised: {exc}\n{traceback.format_exc()}")
                # MCP clients prefer a structured tool-error over a
                # protocol-level error so the chat UI can render it.
                return _ok_response(req_id, {
                    "content": [{
                        "type": "text",
                        "text": f"Error running {name}: {exc}",
                    }],
                    "isError": True,
                })

            # MCP spec: tools/call returns {content: [...]} where each
            # block has a type + payload.
            text = (result.get("summary_text")
                    if isinstance(result, dict) and "summary_text" in result
                    else json.dumps(result, indent=2))
            return _ok_response(req_id, {
                "content": [
                    {"type": "text", "text": text},
                ],
                "structuredContent": result,
                "isError": False,
            })

        if method == "ping":
            return _ok_response(req_id, {})

        if method == "shutdown":
            return _ok_response(req_id, None)

        if is_notification:
            return None
        return _error_response(req_id, -32601, f"Method not found: {method}")

    except Exception as exc:
        _log(f"unhandled error in {method}: {exc}\n{traceback.format_exc()}")
        if is_notification:
            return None
        return _error_response(req_id, -32603, "Internal error", str(exc))


def main() -> None:
    _log(f"server starting (protocol {PROTOCOL_VERSION})")
    while True:
        msg = _read_message()
        if msg is None:
            # EOF or blank line — keep going so the parent process
            # decides when to shut us down by closing stdin.
            if not sys.stdin.readable():
                break
            continue
        response = _handle_request(msg)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _log("interrupted")
