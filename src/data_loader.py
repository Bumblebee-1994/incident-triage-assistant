"""Load incident and KBA Excel files and produce clean text.

Why this lives in its own module:
    - HTML cleaning (TinyMCE markup in KBAs) is non-trivial.
    - The same loaders are reused by training, indexing, and the Flask app.
"""
from __future__ import annotations

import html as _html
import re
import warnings
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

# openpyxl warns about default styles on these files — harmless, silence it.
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


# --- HTML helpers -----------------------------------------------------------

_WS_RE = re.compile(r"\s+")
_NBSP_RE = re.compile(r"[\xa0\u200b\u2028\u2029]")


def clean_html(text: object) -> str:
    """Strip HTML tags, decode entities, and normalize whitespace.

    Robust to:
        - NaN / None / floats (returned as empty string)
        - Plain text with no tags but with entities (e.g. "Item&nbsp;A")
        - TinyMCE output with <p>, <span style=...>, &nbsp;, etc.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text)
    if not s.strip():
        return ""
    if "<" in s:
        # Tagged: parse with BeautifulSoup (which also decodes entities).
        try:
            soup = BeautifulSoup(s, "lxml")
            s = soup.get_text(separator=" ")
        except Exception:
            s = re.sub(r"<[^>]+>", " ", s)
    else:
        # Plain text path — still decode entities like &nbsp;.
        s = _html.unescape(s)
    s = _NBSP_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def normalize_text(text: object) -> str:
    """Lowercase + collapse whitespace. Use for similarity / classification.

    We deliberately keep punctuation and digits — error codes like 'ORA-01017'
    or 'HTTP 503' are highly informative for IT tickets.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return _WS_RE.sub(" ", str(text)).strip().lower()


# --- Loaders ---------------------------------------------------------------


def load_incidents(path: Path | str) -> pd.DataFrame:
    """Load the incident dump and produce a tidy DataFrame.

    Columns guaranteed to exist after this call:
        number, short_description, description, priority, state,
        category, business_service, assignment_group, close_code,
        close_notes, sys_created_on, resolved_at, text
    The 'text' column is the combined, cleaned input we feed to ML.
    """
    df = pd.read_excel(path, engine="openpyxl")

    # Keep only the columns we actually use; rename for safety.
    keep = [
        "number", "short_description", "description",
        "priority", "state", "category", "business_service",
        "assignment_group", "close_code", "close_notes",
        "sys_created_on", "resolved_at",
    ]
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise ValueError(f"Incident file missing expected columns: {missing}")
    df = df[keep].copy()

    # Fill NaNs with empty strings for text fields so concatenation works.
    for col in ["short_description", "description", "close_notes",
                "category", "business_service", "assignment_group",
                "priority", "state", "close_code"]:
        df[col] = df[col].fillna("").astype(str)

    # Build the combined text we use for ML and retrieval.
    df["short_description_clean"] = df["short_description"].map(clean_html)
    df["description_clean"] = df["description"].map(clean_html)
    df["close_notes_clean"] = df["close_notes"].map(clean_html)

    df["text"] = (df["short_description_clean"] + " . "
                  + df["description_clean"]).map(normalize_text)
    df["text"] = df["text"].str.strip(" .")

    # Drop rows where there is literally nothing to learn from.
    df = df[df["text"].str.len() > 0].reset_index(drop=True)
    return df


def load_kbas(path: Path | str) -> pd.DataFrame:
    """Load the KB articles and produce a tidy DataFrame.

    Columns guaranteed after this call:
        kb_number, short_description, introduction, instructions,
        article_body, kb_class, workflow, active, text
    """
    df = pd.read_excel(path, engine="openpyxl")

    rename_map = {
        "Number": "kb_number",
        "Short description": "short_description",
        "Introduction": "introduction",
        "Instructions": "instructions",
        "Article body": "article_body",
        "Class": "kb_class",
        "Workflow": "workflow",
        "Active": "active",
    }
    missing = [c for c in rename_map if c not in df.columns]
    if missing:
        raise ValueError(f"KB file missing expected columns: {missing}")
    df = df[list(rename_map.keys())].rename(columns=rename_map).copy()

    # Filter to publish-ready, active how-to articles only.
    df["active"] = df["active"].fillna(False).astype(bool)
    df = df[df["active"] & (df["workflow"].astype(str).str.lower() == "published")]

    # Clean each text field.
    for col in ["short_description", "introduction", "instructions", "article_body"]:
        df[col] = df[col].map(clean_html)

    # Combined text used for retrieval — short desc weighted twice (it is the title).
    df["text"] = (
        df["short_description"] + " . " + df["short_description"] + " . "
        + df["introduction"] + " . " + df["instructions"] + " . "
        + df["article_body"]
    ).map(normalize_text).str.strip(" .")

    df = df[df["text"].str.len() > 0].reset_index(drop=True)
    return df


if __name__ == "__main__":
    from src.config import load_config
    cfg = load_config()
    inc = load_incidents(cfg.paths.incidents_xlsx)
    kb = load_kbas(cfg.paths.kb_xlsx)
    print(f"Incidents loaded: {len(inc)} rows")
    print(f"KBAs loaded:      {len(kb)} rows")
    print("\nIncident sample:")
    print(inc[["number", "assignment_group", "text"]].head(2).to_string(index=False))
    print("\nKBA sample:")
    print(kb[["kb_number", "short_description"]].head(2).to_string(index=False))
