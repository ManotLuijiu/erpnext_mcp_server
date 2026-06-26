"""Markdown + YAML frontmatter parser for OKF concepts.

Each OKF concept is a Markdown file with optional YAML frontmatter:

    ---
    type: Frappe DocType
    title: Sales Invoice
    tags: [billing, erpnext]
    ---
    # Sales Invoice
    ...body...

This module parses that format using only pyyaml. No Frappe dependency.

Functions:
    parse_concept(text) -> {"frontmatter": dict, "body": str}
    parse_file(path) -> {"frontmatter": dict, "body": str}
    split_frontmatter(text) -> (yaml_text, body_text)  -- raw split
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class OKFParseError(ValueError):
    """Raised when a concept file cannot be parsed."""


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split Markdown into (yaml_text, body).

    Frontmatter is delimited by '---' lines at the very start of the file.
    If no frontmatter is present, returns (None, original_text).
    """
    # Strip leading whitespace/newlines
    stripped = text.lstrip("\ufeff").lstrip()
    if not stripped.startswith("---"):
        return None, text

    # Find the closing '---' line.
    # The opening '---' must be on its own line at the start.
    lines = stripped.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return None, text

    # Find closing delimiter (must be on its own line)
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            close_idx = i
            break
    if close_idx is None:
        # No closing delimiter — treat whole text as body
        return None, text

    yaml_text = "\n".join(lines[1:close_idx])
    body_text = "\n".join(lines[close_idx + 1 :])
    return yaml_text, body_text


def parse_frontmatter(yaml_text: str | None) -> dict[str, Any]:
    """Parse YAML frontmatter text into a dict.

    Returns an empty dict if yaml_text is None or empty.
    Raises OKFParseError if YAML is malformed.
    """
    if not yaml_text or not yaml_text.strip():
        return {}
    try:
        loaded = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise OKFParseError(f"Malformed YAML frontmatter: {e}") from e
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise OKFParseError(
            f"Frontmatter must be a YAML mapping, got {type(loaded).__name__}"
        )
    return loaded


def parse_concept(text: str) -> dict[str, Any]:
    """Parse a full concept (frontmatter + body) from text.

    Returns:
        {"frontmatter": dict, "body": str}

    Body is the raw Markdown content after the closing '---'.
    """
    yaml_text, body = split_frontmatter(text)
    fm = parse_frontmatter(yaml_text)
    return {"frontmatter": fm, "body": body}


def parse_file(path: str | Path) -> dict[str, Any]:
    """Parse a concept file from disk.

    Raises FileNotFoundError if the path doesn't exist.
    """
    p = Path(path)
    return parse_concept(p.read_text(encoding="utf-8"))


def parse_concept_safe(path: str | Path) -> dict[str, Any] | None:
    """Parse a concept file, returning None on any error.

    Useful for scanning bundles where some files may be malformed.
    """
    try:
        return parse_file(path)
    except (FileNotFoundError, OKFParseError, OSError):
        return None
