# How GitHub Copilot Was Used in This Project

> This document is the audit trail of Copilot involvement in the project.
> It exists because GitHub Copilot was a first-class collaborator, not just
> autocomplete. Every section below is verifiable against the code.

---

## TL;DR for judges

| Module | Lines | Copilot involvement | How |
|---|---|---|---|
| `src/data_loader.py` | ~140 | Drafted | Copilot Chat — *"write a robust HTML→text cleaner that handles TinyMCE output, NaN, and pure-text input"* |
| `src/preprocess.py` | ~110 | Drafted | Copilot Chat — *"stratified train/val/test split with rare-class filtering"* |
| `src/train_classifier.py` | ~165 | Drafted + edited | Copilot Edits — refactored from a single function into per-task helper |
| `src/retrieve.py` | ~190 | Drafted | Copilot Chat — produced the dataclasses, lru_cache loaders, and threshold-gated retrieval |
| `src/evaluate.py` | ~210 | Drafted | Copilot Chat — *"matplotlib charts: confusion matrix, per-class F1, retrieval@k, similarity histogram"* |
| `src/generate.py` | ~150 | Hand + Copilot | Copilot suggested the Jinja2 environment setup; templates hand-authored |
| `src/prompts/*.j2` (4 files) | ~200 | Hand-written | Templates designed by us; Copilot suggested Jinja2 syntax fixes |
| `app/server.py` | ~135 | Drafted | Copilot Chat — *"Flask app with /analyze and /sample_incidents endpoints"* |
| `app/static/app.js` | ~165 | Drafted | Copilot Chat — *"vanilla JS dashboard, fetch + tab switching, no framework"* |
| `app/static/style.css` | ~300 | Drafted | Copilot Chat — *"clean enterprise dashboard CSS, no external framework, ~300 lines"* |
| `tests/test_smoke.py` | ~110 | Drafted | Copilot Chat — *"4 smoke tests for config load, HTML cleaner, Jinja templates, no-match path"* |
| `.github/workflows/ci.yml` | ~70 | Drafted | Copilot Chat — *"GitHub Actions: pytest on push, deploy docs/ to Pages on main"* |

**Roughly 80% of code surface was first drafted by Copilot, then human-reviewed and edited.** The remaining 20% (Jinja2 templates, the architecture diagram, evaluation logic) was hand-authored because it required project-specific judgment that benefits from explicit human design.

---

## Custom Copilot instructions

The repository ships with `.github/copilot-instructions.md` — a file Copilot reads automatically and uses to tailor every suggestion. Highlights:

- *"Never introduce dependencies on hosted LLMs in the runtime inference path."*
- *"Never invent KBA references — recommendations come from `src/retrieve.py::retrieve_kbas`."*
- *"All runbook steps must be non-destructive and generic."*

This means new contributors get project-aware suggestions out of the box — Copilot already knows our domain glossary (`incident`, `assignment_group`, `KBA`, `close_code`) and our forbidden patterns.

---

## Representative Copilot Chat prompts (with results)

### Prompt 1 — bootstrapping the data loader

> *"In `src/data_loader.py`, add a function `clean_html(text)` that takes a possibly-HTML string and returns plain text. Must handle: `None`, `NaN`, pure-text input, TinyMCE markup with `<p>`, `<span style=...>`, and `&nbsp;`. Use BeautifulSoup with the lxml parser, fall back to regex stripping if BeautifulSoup raises. Collapse whitespace. Add a fast path for input with no `<` character."*

**Result:** the `clean_html` function in `src/data_loader.py` lines 23–47, including the fast-path optimization that materially speeds up loading the 18k-row incident file. We accepted Copilot's draft with one edit (adding `_NBSP_RE` to handle additional Unicode space variants we noticed in the data).

### Prompt 2 — generating the evaluation charts

> *"In `src/evaluate.py`, write a function `plot_retrieval_at_k(cfg)` that for each test incident computes the top-k similar TRAIN incidents (using the existing `tfidf_incident.joblib` and `incident_matrix.npz`) and measures recall@k for k in [1,3,5,10] — i.e. did at least one of the top-k neighbors share the same `assignment_group`? Plot it with matplotlib, label points with their values, save to `reports/figures/retrieval_at_k.png`. Return the dict so callers can persist it."*

**Result:** a 30-line function that produced the recall@k chart showing 0.873 / 0.959 / 0.976 / 0.992 — one of our strongest demo numbers. Copilot's first draft had an off-by-one in the `np.argsort(-sims, axis=1)[:, :k]` slicing; we caught it because the chart looked too perfect, asked Copilot Chat to debug, and it fixed it on the first try.

### Prompt 3 — the retrieval threshold gate

> *"In `src/retrieve.py`, write `retrieve_kbas(query_text, top_k=None, threshold=None)` that returns at most `top_k` KBA matches whose cosine similarity is **strictly above** `threshold`. If no KBA crosses the threshold, return an empty list — do NOT lower the threshold or relax the filter, ever. Use `lru_cache` on the loader to avoid reloading sparse matrices on every Flask request. Return dataclasses, not raw dicts."*

**Result:** the function in `src/retrieve.py` lines 76–105. The `lru_cache` suggestion was a Copilot improvement we hadn't thought of — it makes the Flask app's first response slow but every subsequent one nearly instant.

### Prompt 4 — Copilot Edits (multi-file refactor)

We used **Copilot Edits** (not just Chat) once: when we realized `train_classifier.py` was originally a single 200-line function. We selected it and asked:

> *"Refactor this into a `_train_one(label_col, cfg, train_df, val_df, test_df)` helper plus a `main()` that calls it twice — once for `assignment_group`, once for `business_service`. Extract a `_load_split` helper. Update imports. Keep behavior identical."*

Copilot Edits produced a multi-file diff (modifying `train_classifier.py` and adding the cross-reference in `pipeline.py`) that we accepted with no edits. Time saved: ~25 minutes of error-prone manual refactoring.

---

## Where Copilot did NOT help

Honest assessment of the boundaries:

- **Jinja2 templates** — Copilot kept trying to introduce LLM calls or non-deterministic phrasing. Templates are fully hand-authored.
- **Architecture decisions** — what to retrieve, where to gate, what to score. These are product decisions; Copilot is a tool, not a product manager.
- **Threshold tuning** — Copilot suggested 0.5 as a default; we picked 0.25 after empirically measuring that the 90th percentile of noise on this dataset is ~0.23.
- **Class-imbalance honesty** — Copilot's first draft of the README claimed "high accuracy across all classes." We rewrote that section to surface the long-tail F1 truth honestly.

---

## Demo moment — live Copilot Chat

During the live demo we will open Copilot Chat in VS Code and ask it to extend the system in real time. The pre-tested prompt is:

> *"Open `src/evaluate.py` and add a new function `plot_routing_accuracy_by_priority(cfg)` that computes top-1 assignment-group accuracy bucketed by incident `priority` field and plots it as a horizontal bar chart. Save to `reports/figures/accuracy_by_priority.png`. Then call it from `main()`."*

Watch Copilot generate ~25 lines of correct, project-aware code (because of `copilot-instructions.md`), run it, and see the new chart appear in the dashboard.

---

## Reproducing the Copilot setup yourself

1. Open this repo in VS Code (or click the **Open in Codespaces** badge in the README — the devcontainer pre-installs Copilot extensions).
2. Make sure GitHub Copilot and GitHub Copilot Chat are signed in.
3. Open Copilot Chat (`Ctrl+Alt+I` on Windows / `⌘+I` on Mac).
4. Ask any question about the codebase. Copilot will use `.github/copilot-instructions.md` as context automatically — try *"explain how retrieve_kbas decides whether to return matches"* and watch it reference the threshold gate.

---

*This document is the source of truth for "how was Copilot used here?" — update it whenever a new significant Copilot session occurs.*
