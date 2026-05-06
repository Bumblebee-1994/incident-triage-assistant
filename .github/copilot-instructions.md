# GitHub Copilot — Project Instructions

> Copilot reads this file automatically and tailors every suggestion in this
> repository to the conventions below. Keep it short, factual, and current.

## What this project is

A hackathon-grade **Incident Triage Assistant**. Given an anonymized
ServiceNow-style incident, the system retrieves similar past tickets and
relevant Knowledge Base Articles (KBAs), then produces four artifacts:

1. an end-user summary,
2. an IT-agent triage brief,
3. a non-destructive runbook checklist,
4. a draft postmortem.

There is **no LLM call in the inference path** — every output is filled into
a Jinja2 template from real retrieval evidence. This is deliberate: it makes
the system fully reproducible and audit-friendly, and judges can verify any
generated claim by tracing it back to a row in the indexed data.

## Core engineering rules Copilot must follow

1. **Never introduce dependencies on hosted LLMs** in the runtime inference
   path. Embeddings, classification, and retrieval stay local. We are happy
   to use Copilot itself for *authoring* code, but `src/` and `app/` must run
   offline.
2. **Never invent KBA references.** Recommendations come from
   `src/retrieve.py::retrieve_kbas`. If similarity is below
   `cfg.retrieval.kba_threshold`, the user-facing template must say
   "No strong KBA match found" — never paraphrase or fabricate.
3. **All runbook steps must be non-destructive and generic.** No host names,
   no production commands, no anything that would touch a live system.
4. **Configuration lives in `config.yaml`.** Do not hardcode paths,
   thresholds, top-k, or split ratios anywhere else.
5. **Every module is independently runnable** as `python -m src.<name>`.
   Preserve this when adding new modules.

## Code style Copilot should produce

- Python 3.11+. Use `from __future__ import annotations` at module top.
- Type hints on every public function. Return types required.
- Docstrings: short module docstring describing purpose and CLI invocation;
  one-line docstrings on internal helpers; full `Args/Returns` on public
  library functions only.
- Use `pathlib.Path`, never `os.path` string concatenation.
- Use `joblib` for sklearn artifacts, `scipy.sparse.save_npz` for matrices.
- Use `pandas` for tabular data, `numpy` for arrays. No `polars`, no `dask`.
- Logging with `print(...)` is acceptable in CLI scripts; the audience is a
  hackathon judge running things in a terminal, not a production SRE.
- Keep functions under ~40 lines. Prefer flat composition over deep nesting.

## What Copilot should NOT suggest

- `requests` / HTTP calls in the inference path.
- Heavyweight frameworks (FastAPI, Django, SQLAlchemy, Celery) — Flask is
  enough; the demo runs on a laptop.
- Model fine-tuning, GPU code, or transformers libraries. Lexical TF-IDF is
  the deliberate baseline and beats fancier options for this dataset size.
- Async/await unless there's a concrete I/O reason. Most of this code is CPU
  bound on small data; sync is simpler and faster to debug.
- New top-level packages without first asking — keep the directory layout
  predictable for judges.

## When asked to add a new feature

Default flow:

1. Add a config block to `config.yaml` if behavior is tunable.
2. Add a function in the most appropriate `src/` module, typed and tested.
3. If it is user-visible, expose it through `src/pipeline.py` as a stage and
   through the Flask `/analyze` response shape if relevant.
4. Add a smoke test in `tests/test_smoke.py` that runs in <1 second and
   does not require trained models.
5. Update `README.md` only if a new run command appears.

## Domain glossary (use these exact terms)

- **Incident** — one row in `incident_dump.xlsx`. Identified by `number`
  (e.g. `INC00538078`).
- **Assignment group** — the team a ticket gets routed to. Primary
  classifier label.
- **Business service** — the affected service line. Secondary classifier
  label, 36 viable classes after filtering.
- **KBA** — Knowledge Base Article. One row in `kb_template_how_to.xlsx`.
  Identified by `kb_number` (e.g. `KB000A8238`).
- **Close code** — the resolution category an incident was closed under.
  Used as a categorical signal for root-cause hypotheses.
- **Threshold gate** — `cfg.retrieval.kba_threshold`. Controls whether a
  KBA is shown to the user. Tuning this is a product decision, not a code
  change — never bypass it in templates.

## Demo-relevant facts (for Copilot Chat answers)

- 18,168 incidents, 9,874 KBAs in raw data; 2,008 KBAs after filtering to
  active+published.
- Train/val/test = 70/15/15 stratified on `assignment_group`.
- Test-set headline metrics: assignment_group accuracy 0.938, weighted-F1
  0.938; business_service weighted-F1 0.68 (macro-F1 0.14 due to long tail).
- Similar-incident retrieval recall@5 = 0.976 against held-out test set.

## When suggesting commits / PRs

- Conventional Commits style: `feat(retrieve): add re-ranking by recency`,
  `fix(generate): handle empty caller_id`, `docs: update demo flow`.
- One concern per commit. PR descriptions should mention which evaluation
  metric the change is expected to move.
