"""Local AI triage agent — runs in the VS Code terminal.

This is the same engine that powers the Flask dashboard, but exposed as
a friendly CLI. Three modes:

  1. One-shot:
       python -m scripts.triage_cli "user cannot login to SAP, account locked"

  2. Inspect a real incident from the test split:
       python -m scripts.triage_cli --incident INC00538078

  3. Interactive REPL:
       python -m scripts.triage_cli --interactive

The REPL is the "agent" experience — type a natural-language description,
get the four artifacts back inline, ask follow-up questions like
"show runbook" or "use threshold 0.4". No API keys, no network calls,
no LLM dependency.

Designed to look polished in a terminal demo: ANSI colours, boxed
sections, condensed tables. Falls back to plain text on Windows
terminals that don't support ANSI.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Any

# Project root must be importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# --- ANSI colour helpers ---------------------------------------------------
# Keep these zero-dependency; we don't want to require `rich` or `colorama`.

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        # Modern Windows Terminals support ANSI; older cmd.exe doesn't.
        # Enable VT processing if we can.
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return False
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VT
            return True
        except Exception:
            return False
    return True


_USE_COLOR = _supports_color()


def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(s: str) -> str: return _c(s, "1")
def dim(s: str) -> str: return _c(s, "2")
def cyan(s: str) -> str: return _c(s, "36")
def green(s: str) -> str: return _c(s, "32")
def yellow(s: str) -> str: return _c(s, "33")
def red(s: str) -> str: return _c(s, "31")
def blue(s: str) -> str: return _c(s, "34")
def magenta(s: str) -> str: return _c(s, "35")


# --- Pretty-printing helpers ----------------------------------------------


def _term_width() -> int:
    return shutil.get_terminal_size((100, 24)).columns


def _hr(char: str = "─") -> str:
    return dim(char * min(_term_width(), 100))


def _section_header(title: str, icon: str = "▸") -> str:
    return f"\n{cyan(bold(icon + '  ' + title))}\n{_hr()}"


def _wrap(text: str, indent: int = 2) -> str:
    width = min(_term_width(), 100) - indent
    pre = " " * indent
    return "\n".join(pre + line for line in textwrap.wrap(text, width=width) or [""])


def _check_models_present() -> bool:
    """Verify the trained models exist before we try to use them."""
    needed = [
        "tfidf_text_ag.joblib",
        "clf_assignment_group.joblib",
        "label_encoder_ag.joblib",
        "tfidf_kb.joblib",
        "kb_matrix.npz",
        "kb_meta.csv",
        "tfidf_incident.joblib",
        "incident_matrix.npz",
        "incident_meta.csv",
    ]
    models_dir = PROJECT_ROOT / "models"
    missing = [f for f in needed if not (models_dir / f).exists()]
    if missing:
        print(red(bold("✘  Trained models are not present.")))
        print(_wrap("Run the pipeline once to build them:", indent=2))
        print(green("   python -m src.pipeline all"))
        print(dim(f"\n   Missing: {', '.join(missing[:3])}"
                  + ("…" if len(missing) > 3 else "")))
        return False
    return True


# --- Output renderers ------------------------------------------------------


def render_predictions(preds: dict[str, Any]) -> None:
    print(_section_header("Predicted routing", icon="🎯"))
    for label, key in [("Assignment group", "assignment_group"),
                       ("Business service", "business_service")]:
        p = preds[key]
        top = p["top3"][0]
        top_conf = f"({top['prob']*100:.1f}% confidence)"
        print(f"  {bold(label):28s}  {green(top['label'])}  {dim(top_conf)}")
        for alt in p["top3"][1:]:
            alt_conf = f"({alt['prob']*100:.1f}%)"
            print(f"  {'':28s}  {dim(alt['label'])}  {dim(alt_conf)}")


def render_kbas(kbas: list[dict], threshold: float) -> None:
    print(_section_header("KBA recommendations", icon="📚"))
    if not kbas:
        print(_wrap(yellow(f"⚠  No KBA passed the {threshold:.2f} similarity "
                           "threshold — no recommendation forced.")))
        return
    for k in kbas:
        score_color = green if k["score"] >= threshold + 0.10 else yellow
        score_str = f"{k['score']:.3f}"
        print(f"  {bold(k['kb_number'])}  {score_color(score_str)}  "
              f"{k['short_description'][:70]}")
        if k.get("introduction"):
            print(_wrap(dim(k["introduction"][:280]), indent=4))


def render_similar_incidents(items: list[dict]) -> None:
    print(_section_header("Top similar historical incidents", icon="🔍"))
    if not items:
        print(_wrap(dim("No similar incidents found.")))
        return
    for s in items[:5]:
        score_str = f"{s['score']:.3f}"
        print(f"  {bold(s['number'])}  {magenta(score_str)}  "
              f"{dim('→')}  {s['short_description'][:70]}")
        close_code_str = f"close_code: {s['close_code']}"
        print(f"    {dim(close_code_str)}")
        if s.get("close_notes_excerpt"):
            print(_wrap(dim(s["close_notes_excerpt"][:240]), indent=4))


def render_artifact(name: str, body: str) -> None:
    icon = {"user_summary": "👤", "it_summary": "🛠️ ",
            "runbook": "📋", "postmortem": "📝"}.get(name, "📄")
    title = name.replace("_", " ").title()
    print(_section_header(f"{title}", icon=icon))
    for line in body.splitlines():
        print(f"  {line}")


# --- Core agent --------------------------------------------------------------


class TriageAgent:
    """Wraps the triage engine with a CLI-friendly interface."""

    def __init__(self) -> None:
        from src.config import load_config
        from src.generate import analyze_incident
        from src.retrieve import (
            predict_assignment_group, predict_business_service,
            retrieve_kbas, retrieve_similar_incidents,
        )
        self.cfg = load_config()
        self._analyze = analyze_incident
        self._predict_ag = predict_assignment_group
        self._predict_bs = predict_business_service
        self._retrieve_kbas = retrieve_kbas
        self._retrieve_sims = retrieve_similar_incidents
        self.last_result: dict | None = None

    # -- Public actions ----------------------------------------------------

    def triage_text(
        self,
        short_description: str,
        description: str = "",
        priority: str = "3 - Moderate",
    ) -> dict:
        incident = {
            "number": "CLI",
            "short_description": short_description,
            "description": description,
            "priority": priority,
            "caller_id": "",
            "sys_created_on": "",
            "resolved_at": "",
        }
        result = self._analyze(incident)
        self.last_result = result
        return result

    def triage_incident_id(self, incident_id: str) -> dict | None:
        """Look up a real incident from the test split and triage it."""
        import pandas as pd
        inc = pd.read_csv(
            self.cfg.paths.processed_dir / "incidents_clean.csv",
            low_memory=False,
        )
        match = inc[inc["number"] == incident_id]
        if match.empty:
            return None
        row = match.iloc[0].to_dict()
        return self.triage_text(
            short_description=str(row.get("short_description", "") or ""),
            description=str(row.get("description", "") or ""),
            priority=str(row.get("priority", "3 - Moderate") or ""),
        )

    # -- Display ----------------------------------------------------------

    def show_summary(self, result: dict) -> None:
        print(_hr("═"))
        render_predictions(result["predictions"])
        render_kbas(result["kba_matches"], result["kba_threshold"])
        render_similar_incidents(result["similar_incidents"])
        print()
        print(dim(f"Tip: type 'show user' / 'show it' / 'show runbook' / "
                  f"'show postmortem' to view the rendered artifacts."))

    def show_artifact(self, name: str) -> None:
        if not self.last_result:
            print(red("No triage result yet — analyze something first."))
            return
        body = self.last_result["rendered"].get(name)
        if not body:
            print(red(f"Unknown artifact: {name}"))
            return
        render_artifact(name, body)


# --- REPL --------------------------------------------------------------------

REPL_HELP = f"""
{bold('Available commands')}
  {green('triage <text>')}                analyze a free-form description
  {green('incident <ID>')}                analyze a real incident from the test split (e.g. INC00538078)
  {green('show user|it|runbook|postmortem')}   display a rendered artifact
  {green('threshold <float>')}            set KBA similarity threshold (current: {{threshold}})
  {green('samples [N]')}                  list N test-split incidents (default 10)
  {green('help')}                         show this help
  {green('exit')} / {green('quit')} / {green('Ctrl+D')}        leave the agent
"""


def run_repl(agent: TriageAgent) -> None:
    print(_hr("═"))
    print(bold(cyan("  Incident Triage Agent — interactive mode")))
    print(dim("  Type 'help' for commands, 'exit' to quit."))
    print(_hr("═"))

    while True:
        try:
            raw = input(green("\n triage> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        cmd = raw.split(maxsplit=1)
        verb = cmd[0].lower()
        rest = cmd[1] if len(cmd) > 1 else ""

        if verb in ("exit", "quit", ":q"):
            break

        if verb == "help":
            print(REPL_HELP.replace("{threshold}", f"{agent.cfg.retrieval.kba_threshold:.2f}"))
            continue

        if verb == "triage":
            if not rest:
                print(yellow("Usage: triage <free-form description>"))
                continue
            result = agent.triage_text(short_description=rest)
            agent.show_summary(result)
            continue

        if verb == "incident":
            if not rest:
                print(yellow("Usage: incident <INC0...>"))
                continue
            result = agent.triage_incident_id(rest.strip())
            if result is None:
                print(yellow(f"Incident {rest} not found in the test split."))
                continue
            agent.show_summary(result)
            continue

        if verb == "show":
            target = (rest or "").strip().lower()
            mapping = {
                "user": "user_summary",
                "user_summary": "user_summary",
                "it": "it_summary",
                "it_summary": "it_summary",
                "runbook": "runbook",
                "postmortem": "postmortem",
            }
            key = mapping.get(target)
            if not key:
                print(yellow("Usage: show user|it|runbook|postmortem"))
                continue
            agent.show_artifact(key)
            continue

        if verb == "threshold":
            try:
                new_thr = float(rest)
            except ValueError:
                print(yellow("Usage: threshold <float between 0 and 1>"))
                continue
            if not 0 < new_thr < 1:
                print(yellow("Threshold must be in (0, 1)"))
                continue
            agent.cfg.retrieval.kba_threshold = new_thr
            # Also patch the underlying retriever default so subsequent
            # calls pick it up (retrieve_kbas reads it from config each call).
            print(green(f"  KBA threshold updated to {new_thr:.2f}"))
            continue

        if verb == "samples":
            try:
                n = int(rest) if rest else 10
            except ValueError:
                n = 10
            import pandas as pd
            inc_path = agent.cfg.paths.processed_dir / "incidents_clean.csv"
            test_path = agent.cfg.paths.splits_dir / "test.csv"
            if not inc_path.exists() or not test_path.exists():
                print(red("Pipeline has not been run. Run: python -m src.pipeline all"))
                continue
            inc = pd.read_csv(inc_path, low_memory=False)
            ids = pd.read_csv(test_path)["number"].tolist()
            rows = inc[inc["number"].isin(ids)].head(n)
            print(_section_header(f"Sample test-split incidents (top {n})", icon="📋"))
            for _, r in rows.iterrows():
                print(f"  {bold(r['number'])}  {dim(str(r['short_description'])[:80])}")
            continue

        # Fallback: assume the user typed a free-form description without "triage".
        result = agent.triage_text(short_description=raw)
        agent.show_summary(result)

    print(dim("Bye."))


# --- Entry point -------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local AI agent for incident triage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              python -m scripts.triage_cli "user cannot login to SAP"
              python -m scripts.triage_cli --incident INC00538078
              python -m scripts.triage_cli --interactive
        """),
    )
    parser.add_argument("text", nargs="?",
                        help="Free-form incident description (one-shot mode).")
    parser.add_argument("--incident", help="Triage a real incident by its number.")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Start the interactive REPL.")
    parser.add_argument("--show", choices=["user", "it", "runbook", "postmortem", "all"],
                        help="After triage, also print this artifact (or 'all').")
    parser.add_argument("--json", action="store_true",
                        help="Emit raw JSON instead of pretty output (for piping).")
    args = parser.parse_args()

    if not _check_models_present():
        sys.exit(2)

    agent = TriageAgent()

    if args.interactive:
        run_repl(agent)
        return

    # One-shot mode.
    if args.incident:
        result = agent.triage_incident_id(args.incident)
        if result is None:
            print(red(f"Incident {args.incident} not found in test split."))
            sys.exit(1)
    elif args.text:
        result = agent.triage_text(short_description=args.text)
    else:
        # No args at all — drop into REPL.
        run_repl(agent)
        return

    if args.json:
        import json
        # Strip rendered artifacts from JSON to keep it compact unless asked.
        compact = {
            "predictions": result["predictions"],
            "kba_matches": result["kba_matches"],
            "similar_incidents": result["similar_incidents"],
            "kba_threshold": result["kba_threshold"],
        }
        print(json.dumps(compact, indent=2))
        return

    agent.show_summary(result)
    if args.show == "all":
        for k in ("user_summary", "it_summary", "runbook", "postmortem"):
            agent.show_artifact(k)
    elif args.show:
        mapping = {"user": "user_summary", "it": "it_summary",
                   "runbook": "runbook", "postmortem": "postmortem"}
        agent.show_artifact(mapping[args.show])


if __name__ == "__main__":
    main()
