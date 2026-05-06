# Incident Triage Assistant

A solution for a Microsoft GitHub Copilot hackathon. Ingests anonymized ServiceNow-style incident tickets and Knowledge Base Articles (KBAs), then for any incident produces:

1. A concise **end-user summary** with safe self-resolution suggestions (only when KBA confidence is high).
2. An **IT-agent summary** with predicted assignment group, ranked root-cause hypotheses from similar past tickets, and KBA references.
3. An **actionable runbook** with non-destructive, generic steps.
4. A **draft postmortem** with auto-filled metadata and `[BLANK]` markers for owner input.
5. **Evaluation metrics** with confusion matrices, per-class F1, retrieval@k, and similarity distribution charts.
6. A **simple polished UI**, both as a live Flask app and as a static GitHub Pages page.

---

## Why this design

- **TF-IDF + Logistic Regression** for assignment-group and business-service prediction. Trains in under a minute, fully explainable, no GPU.
- **TF-IDF + cosine similarity** for KBA matching, with a configurable threshold so low-confidence matches are *never forced* — the UI explicitly says "No strong KBA match found" instead.
- **Jinja2 templates** for all generated artifacts. Variables come from real retrieval results, so the system cannot hallucinate. Replace this layer with an LLM later if you want richer phrasing — the data flow stays identical.
- **End-to-end runs on a laptop in 4–6 hours**: no fine-tuning, no vector DB, no external APIs.

---
incident-triage-assistant-final/
├── README.md, requirements.txt, .gitignore, config.yaml
├── data/raw/                       # YOUR Excel files (included)
├── docs/                           # Static GitHub Pages demo (open docs/index.html now!)
│   ├── index.html                  # Self-contained, 5 sample analyses inlined
│   └── figures/                    # 6 charts
├── src/                            # 12 Python modules + 4 Jinja2 templates
├── app/                            # Flask + HTML/CSS/JS dashboard
├── reports/                        # Pre-rendered: 6 charts, 4 metrics files, 20 sample .md
├── tests/test_smoke.py             # 4 smoke tests
├── notebooks/01_eda.ipynb          # 10-cell EDA notebook
└── .github/workflows/ci.yml        # CI: tests + Pages deploy

---

## Quickstart (VS Code terminal)

```bash
# 1. Clone and enter
git clone https://github.com/<you>/incident-triage-assistant.git
cd incident-triage-assistant

# 2. Create a virtual environment
python -m venv .venv
# Mac/Linux:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Drop your data files into data/raw/
#    (incident_dump.xlsx and kb_template_how_to.xlsx)

# 5. Run the full pipeline (~2 minutes total)
python -m src.pipeline all

# 6. Launch the live demo UI
python -m app.server
# Open http://127.0.0.1:5000

# 7. (Optional) View the static GitHub Pages snapshot locally
cd docs && python -m http.server 8000
# Open http://127.0.0.1:8000
```

### Stage-by-stage (if you want to step through)

```bash
python -m src.preprocess              # ~10 sec — clean + split
python -m src.train_classifier        # ~30 sec — train both classifiers
python -m src.build_kb_index          # ~5 sec  — KBA TF-IDF index
python -m src.build_incident_index    # ~10 sec — historic-ticket index
python -m src.generate --num 5        # ~10 sec — render 5 sample artifacts
python -m src.evaluate                # ~30 sec — metrics + charts
python -m src.build_static_docs       # ~2 sec  — static demo page
python -m pytest tests/ -v            # ~5 sec  — smoke tests
```

---

## What goes where

| Path | What it is |
|---|---|
| `config.yaml` | Single source of truth for paths, thresholds, model params |
| `data/raw/` | Your two Excel files (gitignored) |
| `data/processed/` | Cleaned CSVs after `preprocess` |
| `data/splits/` | Reproducible train/val/test ID lists |
| `models/` | Joblib + npz artifacts (gitignored) |
| `reports/figures/` | Confusion matrices and other charts |
| `reports/metrics/` | JSON metrics + summary CSV |
| `reports/samples/` | Pre-rendered sample artifacts (committed) |
| `src/` | All Python modules — every file is independently runnable |
| `src/prompts/` | Jinja2 templates (NOT free-form LLM prompts) |
| `app/` | Flask backend + static HTML/CSS/JS dashboard |
| `docs/` | Static GitHub Pages snapshot |
| `tests/` | Smoke tests run by CI |
| `.github/workflows/ci.yml` | CI: tests on every push, deploys docs/ on main |

---

---

## How to extend this for production (post-hackathon)

These are *not* in scope for the hackathon, but useful talking points:

- Replace TF-IDF with sentence-transformer embeddings for semantic KBA matching.
- Replace the Jinja2 templates with LLM prompts that ingest the *same* retrieval evidence — you get nicer phrasing without losing groundedness.
- Add active learning: surface tickets where top-1 confidence is low, route to humans for labels, retrain.
- Plug in a real ITSM API (ServiceNow `incident.do`) once data governance and security review are complete.
- Per-class precision/recall thresholds: predict only when calibrated probability is above a class-specific threshold.

---


---

## License

MIT — do whatever you want with this code.
