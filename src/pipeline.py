"""End-to-end pipeline orchestrator.

Run any single stage or the whole thing:
    python -m src.pipeline all
    python -m src.pipeline preprocess
    python -m src.pipeline train
    python -m src.pipeline index
    python -m src.pipeline generate
    python -m src.pipeline evaluate
"""
from __future__ import annotations

import argparse
import sys
import time

from src import (
    build_incident_index,
    build_kb_index,
    build_static_docs,
    evaluate,
    generate,
    preprocess,
    train_classifier,
)


STAGES = {
    "preprocess": ("Clean data + make stratified splits", preprocess.main),
    "train":      ("Train both classifiers",              train_classifier.main),
    "index":      ("Build KB and incident retrieval indexes", lambda: (build_kb_index.main(), build_incident_index.main())),
    "generate":   ("Render sample artifacts for demo",    generate.main),
    "evaluate":   ("Compute metrics + charts",            evaluate.main),
    "docs":       ("Build static GitHub Pages page",      build_static_docs.main),
}


def run_stage(name: str) -> None:
    if name not in STAGES:
        print(f"Unknown stage: {name}", file=sys.stderr)
        sys.exit(2)
    desc, fn = STAGES[name]
    t0 = time.time()
    print(f"\n{'#'*60}\n#  {name.upper()}: {desc}\n{'#'*60}")
    fn()
    print(f"--> {name} finished in {time.time() - t0:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline orchestrator.")
    parser.add_argument(
        "stage",
        choices=["all"] + list(STAGES.keys()),
        help="Stage to run, or 'all' for the full pipeline.",
    )
    args = parser.parse_args()

    if args.stage == "all":
        for name in ["preprocess", "train", "index", "generate", "evaluate", "docs"]:
            run_stage(name)
    else:
        run_stage(args.stage)
    print("\nDone.")


if __name__ == "__main__":
    main()
