"""Load config.yaml into a typed object the rest of the code uses.

We use a plain SimpleNamespace so attribute access works
(`cfg.paths.incidents_xlsx`) without pydantic as a dependency.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def _to_namespace(obj: Any) -> Any:
    """Recursively convert a dict tree to nested SimpleNamespaces."""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_namespace(v) for v in obj]
    return obj


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> SimpleNamespace:
    """Load YAML config and resolve all paths relative to project root."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Resolve every value under `paths:` to an absolute Path object.
    paths = raw.get("paths", {})
    for key, val in paths.items():
        paths[key] = (PROJECT_ROOT / val).resolve()

    cfg = _to_namespace(raw)
    cfg.project_root = PROJECT_ROOT
    return cfg


if __name__ == "__main__":
    # Quick smoke test: print the loaded config.
    cfg = load_config()
    print(f"Project root: {cfg.project_root}")
    print(f"Incidents:    {cfg.paths.incidents_xlsx}")
    print(f"KB:           {cfg.paths.kb_xlsx}")
    print(f"KBA threshold: {cfg.retrieval.kba_threshold}")
