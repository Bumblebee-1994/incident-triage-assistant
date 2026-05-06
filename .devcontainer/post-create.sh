#!/usr/bin/env bash
# Post-create hook — runs once after the Codespace / devcontainer starts.
# Installs Python deps and (if data is present) runs the full pipeline so
# the demo is hot the moment the user opens VS Code.

set -euo pipefail

echo "================================================================"
echo "  Incident Triage Assistant — Codespace bootstrap"
echo "================================================================"

cd "$(dirname "$0")/.."

echo ">> Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# If the raw data is present, run the pipeline so the demo is ready.
# Skip this step gracefully when running on a fresh Codespace where the
# data has not been added yet.
if [ -f "data/raw/incident_dump.xlsx" ] && [ -f "data/raw/kb_template_how_to.xlsx" ]; then
  echo ""
  echo ">> Raw data found — running full pipeline (~2 minutes)..."
  python -m src.pipeline all || {
    echo "!! Pipeline failed — you can re-run it manually with:"
    echo "   python -m src.pipeline all"
  }
else
  echo ""
  echo ">> No raw data in data/raw/ — pipeline skipped."
  echo "   Drop incident_dump.xlsx and kb_template_how_to.xlsx into data/raw/,"
  echo "   then run:  python -m src.pipeline all"
fi

echo ""
echo "================================================================"
echo "  Bootstrap done."
echo ""
echo "  Next steps:"
echo "    python -m app.server          # live demo at http://localhost:5000"
echo "    python -m scripts.triage_cli  # CLI agent (see scripts/triage_cli.py)"
echo "    python -m scripts.mcp_server  # MCP server for agentic tools"
echo "================================================================"
