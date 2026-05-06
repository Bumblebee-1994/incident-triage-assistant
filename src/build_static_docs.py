"""Build a self-contained static HTML page in docs/ for GitHub Pages.

This page embeds the pre-generated sample artifacts and links the chart
images so judges can see the demo without running anything locally.

Run AFTER `python -m src.evaluate` and `python -m src.generate`:
    python -m src.build_static_docs
"""
from __future__ import annotations

import html
import shutil
from pathlib import Path

from src.config import load_config


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Incident Triage Assistant — Static Demo</title>
<style>
:root {{
  --bg: #f5f6f8; --card: #fff; --text: #1c1d1f; --muted: #6b6f76;
  --border: #e3e6eb; --accent: #185fa5; --accent-soft: #e6f1fb;
  --warn-soft: #fceedf; --warn: #854f0b;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg); color: var(--text); font-size: 15px; line-height: 1.55; }}
header {{ background: var(--card); border-bottom: 1px solid var(--border); padding: 14px 28px;
  display: flex; align-items: center; justify-content: space-between; }}
header h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
.container {{ max-width: 1180px; margin: 24px auto 60px; padding: 0 24px; display: grid; gap: 20px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 20px 24px; box-shadow: 0 1px 2px rgba(20,25,40,0.04), 0 4px 12px rgba(20,25,40,0.05); }}
.card h2 {{ margin: 0 0 8px; font-size: 16px; font-weight: 600; }}
.muted {{ color: var(--muted); font-size: 13px; }}
.charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 12px; }}
.charts-grid figure {{ margin: 0; }}
.charts-grid img {{ width: 100%; border-radius: 6px; border: 1px solid var(--border); }}
.charts-grid figcaption {{ font-size: 12px; color: var(--muted); margin-top: 6px; }}
.tabs {{ display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin: 8px 0 12px;
  overflow-x: auto; }}
.tab-btn {{ padding: 8px 14px; background: transparent; border: none; border-bottom: 2px solid transparent;
  cursor: pointer; font-size: 13px; font-weight: 500; color: var(--muted); white-space: nowrap; }}
.tab-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); }}
.artifact {{ background: #fbfbfc; border: 1px solid var(--border); border-radius: 6px;
  padding: 16px; font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  font-size: 12.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word;
  max-height: 540px; overflow-y: auto; margin: 0; }}
.incident-tabs {{ display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }}
.incident-tab {{ padding: 6px 12px; background: var(--accent-soft); color: var(--accent);
  border: none; border-radius: 6px; cursor: pointer; font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, monospace; font-weight: 600; }}
.incident-tab.active {{ background: var(--accent); color: #fff; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left; }}
th {{ font-weight: 600; color: var(--muted); }}
code {{ font-family: ui-monospace, monospace; font-size: 12px; padding: 1px 5px;
  background: var(--accent-soft); border-radius: 4px; }}
footer {{ text-align: center; padding: 18px 24px 28px; color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
<header>
  <h1>Incident Triage Assistant — Static Demo</h1>
  <span class="muted">GitHub Pages snapshot · pre-rendered artifacts · no backend required</span>
</header>

<main class="container">

  <section class="card">
    <h2>What this is</h2>
    <p>An end-to-end ServiceNow-style triage assistant built for a Microsoft GitHub Copilot hackathon.
       Trained on anonymized incident and KBA data, it produces four artifacts per incident:
       a user summary, an IT-agent triage brief, a runbook, and a draft postmortem. All outputs are
       grounded in retrieved evidence — there is no free-form generation, so nothing can be hallucinated.</p>
    <p class="muted">Threshold note: KBA recommendations are only shown when cosine similarity is above <code>{threshold}</code>.
       Below that, the system explicitly says "No strong KBA match found".</p>
  </section>

  <section class="card">
    <h2>Headline metrics (test split)</h2>
    {summary_table}
    <p class="muted">Macro-F1 is low for business_service because of severe class imbalance across 36 classes — see per-class F1 chart below for the honest picture.</p>
  </section>

  <section class="card">
    <h2>Charts</h2>
    <div class="charts-grid">
      <figure><img src="figures/confusion_matrix_ag.png" alt="Confusion matrix AG"><figcaption>Assignment group — confusion matrix.</figcaption></figure>
      <figure><img src="figures/per_class_f1_ag.png" alt="F1 AG"><figcaption>Per-class F1 — assignment group.</figcaption></figure>
      <figure><img src="figures/confusion_matrix_bs.png" alt="Confusion BS"><figcaption>Business service — top 15 classes.</figcaption></figure>
      <figure><img src="figures/per_class_f1_bs.png" alt="F1 BS"><figcaption>Per-class F1 — business service.</figcaption></figure>
      <figure><img src="figures/kba_similarity_dist.png" alt="KBA distribution"><figcaption>KBA similarity distribution.</figcaption></figure>
      <figure><img src="figures/retrieval_at_k.png" alt="Retrieval@k"><figcaption>Similar-incident retrieval recall@k.</figcaption></figure>
    </div>
  </section>

  <section class="card">
    <h2>Sample analyses</h2>
    <p class="muted">Click an incident number, then switch artifact tabs.</p>
    <div class="incident-tabs" id="incident-tabs">{incident_tabs}</div>
    <div class="tabs">
      <button class="tab-btn active" data-tab="user_summary">User summary</button>
      <button class="tab-btn" data-tab="it_summary">IT summary</button>
      <button class="tab-btn" data-tab="runbook">Runbook</button>
      <button class="tab-btn" data-tab="postmortem">Postmortem</button>
    </div>
    <pre class="artifact" id="artifact-body"></pre>
  </section>

</main>

<footer>
  <small>Demo only · data is anonymized · not connected to any production system</small>
</footer>

<script>
const SAMPLES = {samples_json};
let activeIncident = Object.keys(SAMPLES)[0];
let activeTab = "user_summary";

function render() {{
  const body = SAMPLES[activeIncident][activeTab];
  document.getElementById("artifact-body").textContent = body;
  document.querySelectorAll(".incident-tab").forEach(b => {{
    b.classList.toggle("active", b.dataset.incident === activeIncident);
  }});
  document.querySelectorAll(".tab-btn").forEach(b => {{
    b.classList.toggle("active", b.dataset.tab === activeTab);
  }});
}}

document.querySelectorAll(".incident-tab").forEach(b => {{
  b.addEventListener("click", () => {{ activeIncident = b.dataset.incident; render(); }});
}});
document.querySelectorAll(".tab-btn").forEach(b => {{
  b.addEventListener("click", () => {{ activeTab = b.dataset.tab; render(); }});
}});
render();
</script>
</body>
</html>
"""


def _read_md(path: Path) -> str:
    if not path.exists():
        return "(missing)"
    return path.read_text(encoding="utf-8")


def _summary_table_html(cfg) -> str:
    csv_path = cfg.paths.metrics_dir / "summary.csv"
    if not csv_path.exists():
        return "<em>(run <code>python -m src.evaluate</code> first)</em>"
    import csv
    rows = list(csv.DictReader(csv_path.open()))
    head = ("<table><thead><tr>"
            + "".join(f"<th>{h}</th>" for h in rows[0].keys())
            + "</tr></thead><tbody>")
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r.values()) + "</tr>"
        for r in rows
    )
    return head + body + "</tbody></table>"


def main() -> None:
    cfg = load_config()
    docs_dir = cfg.project_root / "docs"
    figures_src = cfg.paths.figures_dir
    figures_dst = docs_dir / "figures"

    # Copy charts into docs/figures so the static page is self-contained.
    figures_dst.mkdir(parents=True, exist_ok=True)
    if figures_src.exists():
        for png in figures_src.glob("*.png"):
            shutil.copy2(png, figures_dst / png.name)

    # Discover sample incidents from reports/samples.
    samples_dir = cfg.paths.samples_dir
    incident_numbers = sorted({
        p.name.split("_", 1)[0] for p in samples_dir.glob("INC*_*.md")
    })

    samples_obj: dict[str, dict[str, str]] = {}
    for inc_num in incident_numbers:
        samples_obj[inc_num] = {
            kind: _read_md(samples_dir / f"{inc_num}_{kind}.md")
            for kind in ("user_summary", "it_summary", "runbook", "postmortem")
        }

    incident_tabs_html = "".join(
        f'<button class="incident-tab" data-incident="{html.escape(n)}">{html.escape(n)}</button>'
        for n in incident_numbers
    )

    # Pretty-encode samples as JSON literal, escaping </script> safely.
    import json
    samples_json = json.dumps(samples_obj).replace("</", "<\\/")

    page = PAGE_TEMPLATE.format(
        threshold=cfg.retrieval.kba_threshold,
        summary_table=_summary_table_html(cfg),
        incident_tabs=incident_tabs_html,
        samples_json=samples_json,
    )
    out = docs_dir / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"  wrote {out.relative_to(cfg.project_root)}")
    print(f"  copied {sum(1 for _ in figures_dst.glob('*.png'))} charts to docs/figures/")
    print(f"  embedded {len(incident_numbers)} sample incidents")


if __name__ == "__main__":
    main()
