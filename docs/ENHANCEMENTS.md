# Enhanced Features — Overlay README

> This file documents the features added by the **enhancement overlay**. The
> base `README.md` still describes the core pipeline. Everything here is
> additive — none of the original functionality is touched.

---

## What this overlay adds

| Feature | What it gives you | Score impact |
|---|---|---|
| `.github/copilot-instructions.md` | Copilot reads this automatically and tailors every suggestion to project conventions | Solution Quality +2 |
| `COPILOT_USAGE.md` | Audit trail of how Copilot was used; demo evidence for judges | Solution Quality +1, Innovation +1 |
| `BUSINESS_CASE.md` | KONE-specific ROI math, productionization roadmap | Business Impact +2 |
| `.devcontainer/` | Click-to-run in GitHub Codespaces; no local setup | Practical Usability +1 |
| `.github/workflows/triage-issue.yml` | New issues get auto-triaged via GitHub Action | Innovation +2, Practical Usability +1 |
| `scripts/mcp_server.py` | MCP-protocol server so Claude Desktop / agentic tools can call the engine | Innovation +2 |
| `scripts/triage_cli.py` | **The headline new feature**: a polished local AI agent in your terminal | Innovation +2, Usability +1 |
| `.github/ISSUE_TEMPLATE/incident.yml` | Structured issue form that triggers the auto-triage workflow | Polish |

Combined: roughly **+8 to +10 points** vs the base submission.

---

## 1. The Copilot CLI agent (most demo-able)

The single most impressive new feature for a live demo.

### One-shot — fastest way to show it works

```bash
python -m scripts.triage_cli "user cannot login to SAP, account locked"
```

Output is colour-coded and boxed: predicted routing (top-3 each for
assignment group and business service), KBA matches with confidence
scores, top-5 similar historical incidents with their close-codes and
notes excerpts.

### Triage a real incident from the test set

```bash
python -m scripts.triage_cli --incident INC00538078
```

### Show one of the four artifacts inline

```bash
python -m scripts.triage_cli "user cannot reset password" --show user
python -m scripts.triage_cli --incident INC00538078 --show all
```

### Interactive REPL — the "agent" experience

```bash
python -m scripts.triage_cli --interactive
```

Then type natural-language commands:

```
 triage> user cannot login to SAP, account locked
 [results displayed inline]

 triage> show runbook
 [the safe, non-destructive runbook is displayed]

 triage> samples 5
 [lists 5 real test-split incidents you could analyse]

 triage> incident INC00538078
 [pulls a real ticket from the test set and analyses it]

 triage> threshold 0.4
   KBA threshold updated to 0.40

 triage> exit
```

### JSON mode for piping

```bash
python -m scripts.triage_cli "issue text" --json | jq '.predictions.assignment_group.top1'
```

This is what makes the CLI an actual "agent": same engine as the Flask
app, callable from any shell pipeline, scriptable in `make` or `npm`
hooks, embeddable in higher-level orchestration.

---

## 2. The MCP server — for agentic tooling

Wraps the triage engine as a Model Context Protocol server so any
MCP-aware client (Claude Desktop, Continue, etc.) can call it as a tool.

### Run it

```bash
python -m scripts.mcp_server
```

The server reads JSON-RPC messages on stdin and writes responses on
stdout. The server is silent on stdout until a client speaks first; that
is normal MCP behavior.

### Claude Desktop config example

Add to `claude_desktop_config.json` (Windows path:
`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "incident-triage": {
      "command": "python",
      "args": ["-m", "scripts.mcp_server"],
      "cwd": "C:/full/absolute/path/to/incident-triage-assistant-final"
    }
  }
}
```

Restart Claude Desktop. You will see two new tools available:

- `triage_incident(short_description, description?, priority?)` — runs the full triage pipeline.
- `list_sample_incidents(limit?)` — returns real incident IDs you could try.

Now you can chat with Claude and ask things like *"triage this: 'PO not generating in SAP after MRP run'"* — Claude calls the MCP tool, gets back grounded predictions and similar historical incidents, and explains the result.

### Why it matters for the hackathon

This demonstrates that the same engine is callable from the IDE (Copilot
chat), the terminal (CLI agent), the browser (Flask UI), GitHub
(workflow), and any agentic AI tool (MCP). One backend, five surfaces.

---

## 3. Auto-triage GitHub Action

The workflow `.github/workflows/triage-issue.yml` runs whenever someone
opens an issue with the `incident` label. It:

1. Builds (or restores from cache) the trained models.
2. Runs the CLI helper on the issue body.
3. Posts a comment with predicted routing, KBA matches, and similar
   historical incidents.
4. Auto-applies a label like `triage:KONE.SAP.Security.AMS`.

### Try it manually

After pushing the overlay to GitHub:

1. **Settings → Actions → General → Workflow permissions →** "Read and write permissions" (so the workflow can comment + label).
2. Open a new issue using the **🚨 Incident — request auto-triage** template.
3. Within ~1 minute the bot comments with the analysis.

You can also trigger it manually from the **Actions** tab via *Run workflow*.

---

## 4. Codespaces / devcontainer

Add this badge to the top of your main `README.md`:

```markdown
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/<your-username>/incident-triage-assistant?quickstart=1)
```

Replace `<your-username>` with your GitHub handle. Clicking it spins up a
full VS Code in the browser, pre-installs all dependencies, runs the
pipeline if data is present, and forwards ports 5000 (Flask) and 8000
(static GH Pages preview).

For judges who don't want to clone — this is the lowest-friction demo
path possible.

---

## 5. Demo flow update

If you only have 5 minutes, here is the new demo flow that uses the
enhancements:

| Time | What to do | Talking point |
|---|---|---|
| 0:00–0:30 | Show `BUSINESS_CASE.md` quickly | "750 hours/year saved, no LLM, no data leaves the network" |
| 0:30–1:30 | Open static `docs/index.html`, click two incidents | "Threshold gate — never forces a KBA recommendation" |
| 1:30–2:30 | **In VS Code terminal:** `python -m scripts.triage_cli --interactive` | "Same engine as the dashboard, but as a local AI agent — useful for IT ops in shells" |
| 2:30–3:30 | **Open Copilot Chat** and ask it to add a feature | "We have `.github/copilot-instructions.md` so Copilot understands our domain" |
| 3:30–4:15 | Show the auto-triage Action firing on a fresh issue | "Same engine, GitHub-native deployment — 80 lines of YAML" |
| 4:15–5:00 | Show MCP server config in Claude Desktop OR walk through the eval charts | "One engine, five surfaces. This is the production path." |

---

## File map (overlay only)

```
.github/
├── copilot-instructions.md          # Copilot reads automatically
├── ISSUE_TEMPLATE/
│   └── incident.yml                 # Triggers the auto-triage workflow
└── workflows/
    └── triage-issue.yml             # The auto-triage Action

.devcontainer/
├── devcontainer.json                # Codespaces config
└── post-create.sh                   # Bootstrap script

scripts/
├── __init__.py
├── triage_cli.py                    # Local AI agent (the headline feature)
├── mcp_server.py                    # MCP server for agentic tools
└── triage_issue_body.py             # Helper for the GitHub Action

docs/
└── ENHANCEMENTS.md                  # This file

COPILOT_USAGE.md                     # Copilot audit trail
BUSINESS_CASE.md                     # KONE ROI / productionization
```

Nothing in `src/`, `app/`, or `data/` was modified. Drop this overlay
on top of the existing project and it just works.
