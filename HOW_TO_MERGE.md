# Enhancement Overlay — Incident Triage Assistant

> **A drop-in upgrade that adds Copilot/GitHub showcase features to your
> existing project without modifying any existing files.**

---

## What this overlay contains

13 new files across 6 directories. **Zero modifications to any existing
file in your project.** All additions are net-new.

```
.devcontainer/devcontainer.json            # Codespaces config
.devcontainer/post-create.sh               # Codespaces bootstrap

.github/copilot-instructions.md            # Custom Copilot instructions
.github/ISSUE_TEMPLATE/incident.yml        # Triggers the auto-triage Action
.github/workflows/triage-issue.yml         # The auto-triage GitHub Action

scripts/__init__.py                        # Package marker
scripts/triage_cli.py                      # 🌟 Local AI agent (terminal)
scripts/mcp_server.py                      # 🌟 MCP server for agentic tools
scripts/triage_issue_body.py               # Helper for the Action

tests/test_enhancements.py                 # 9 smoke tests for the overlay

docs/ENHANCEMENTS.md                       # Detailed feature guide

BUSINESS_CASE.md                           # KONE ROI / productionization
COPILOT_USAGE.md                           # Copilot audit trail
```

---

## How to merge — exact steps for VS Code on Windows

You should see a sibling zip file named **`incident-triage-overlay.zip`** along
with the original project. Here is the simplest, safest merge process.

### Option A — File Explorer copy (easiest, recommended)

1. Right-click `incident-triage-overlay.zip` → **Extract All…** → choose any
   convenient location (e.g. your `Downloads` folder).
2. Open the extracted folder. You should see something like
   `incident-triage-overlay/` containing `BUSINESS_CASE.md`, `COPILOT_USAGE.md`,
   `.github/`, `.devcontainer/`, `scripts/`, `docs/`, `tests/`.
3. **Select all contents** of that folder (Ctrl+A).
4. **Copy** (Ctrl+C).
5. Open File Explorer in your existing project folder
   (`incident-triage-assistant-final\`).
6. **Paste** (Ctrl+V) directly into the project root.
7. When Windows asks about merging the `.github`, `docs`, and `tests`
   folders → click **"Replace the files in the destination"** for those
   folders. *(Don't worry — none of the new files share names with existing
   ones, so nothing actually gets replaced. Windows just asks because the
   folder names match.)*

✅ Done. No file from the original project is overwritten.

### Option B — From the VS Code terminal (if you prefer CLI)

Open a PowerShell terminal **in the project root** (the folder that
contains `README.md`, `config.yaml`, `src/`, etc.) and run:

```powershell
# Extract the overlay zip into a temporary folder next to the project.
Expand-Archive -Path C:\path\to\incident-triage-overlay.zip -DestinationPath ..\overlay-tmp -Force

# Copy everything from that temp folder INTO the current project, preserving
# directory structure. -Force will overwrite same-named files (none in our case).
Copy-Item -Path ..\overlay-tmp\incident-triage-overlay\* -Destination . -Recurse -Force

# Clean up.
Remove-Item -Recurse -Force ..\overlay-tmp
```

### Option C — Mac / Linux

```bash
unzip incident-triage-overlay.zip -d /tmp/overlay
cp -rn /tmp/overlay/incident-triage-overlay/* ./   # -n = no-clobber, never overwrite
cp -rn /tmp/overlay/incident-triage-overlay/.github ./
cp -rn /tmp/overlay/incident-triage-overlay/.devcontainer ./
rm -rf /tmp/overlay
```

---

## Verify the merge worked

After merging, run these from the project root to confirm everything is
in place and nothing existing has been broken:

```bash
# 1. Smoke-test the overlay (9 tests, ~2 sec, no models needed)
python -m pytest tests/test_enhancements.py -v

# 2. Smoke-test that originals still pass (4 tests)
python -m pytest tests/test_smoke.py -v

# 3. Try the new CLI agent (REQUIRES models — run python -m src.pipeline all first)
python -m scripts.triage_cli "user cannot login to SAP, account locked"
```

If all three pass / produce output, the overlay is correctly applied.

---

## Quick-start the new features

```bash
# 1. Run the pipeline if you haven't already (~2 min)
python -m src.pipeline all

# 2. Try the local AI agent — one-shot
python -m scripts.triage_cli "PO not generating in SAP after MRP run"

# 3. Try the local AI agent — interactive REPL
python -m scripts.triage_cli --interactive

# 4. Triage a real test-set incident
python -m scripts.triage_cli --incident INC00538078 --show all

# 5. Run the MCP server (for Claude Desktop integration)
python -m scripts.mcp_server
```

For full details on each feature, see **`docs/ENHANCEMENTS.md`** (added by
this overlay).

---

## What changed in the original code?

**Nothing.** This is a strictly additive overlay. No edits to:
- `src/` (any module)
- `app/` (Flask backend, HTML, CSS, JS)
- `data/` (raw or processed)
- `models/`, `reports/`
- `config.yaml`, `requirements.txt`, `README.md`, `.gitignore`
- `tests/test_smoke.py` (the original 4 tests)
- `.github/workflows/ci.yml` (the original CI)

Your previous demo flow continues to work exactly as before. The new
features simply add additional surfaces for the same engine.

---

## Final check before submission

- [ ] `python -m pytest tests/ -v` shows **13 tests passing** (4 original + 9 new).
- [ ] `python -m scripts.triage_cli "test query"` produces colourful output.
- [ ] `python -m app.server` still launches the Flask UI on port 5000.
- [ ] `BUSINESS_CASE.md` and `COPILOT_USAGE.md` are visible at the project root.
- [ ] `.github/copilot-instructions.md` exists.

If all five are ✅, you are ready to submit.
