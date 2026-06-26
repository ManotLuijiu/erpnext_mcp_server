"""Markdown + frontmatter writer for OKF concepts.

Writes a concept to disk with:
  - YAML frontmatter (sorted keys for stable diffs)
  - Blank line separator
  - Markdown body

Also exposes assemble_concept() for in-memory assembly (used by tests).

No Frappe dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class OKFWriteError(IOError):
    """Raised when a concept cannot be written."""


def dump_frontmatter(frontmatter: dict[str, Any]) -> str:
    """Serialize frontmatter dict to YAML block.

    Uses block style, sorts keys, and forces utf-8.
    Returns the YAML string WITHOUT the surrounding '---' delimiters.
    """
    if not frontmatter:
        return ""
    # default_flow_style=False gives readable block YAML
    return yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=True,
        allow_unicode=True,
        width=120,
    ).rstrip()


def assemble_concept(frontmatter: dict[str, Any], body: str) -> str:
    """Build a complete concept text from frontmatter + body.

    Format:
        ---
        <yaml>
        ---

        <body>

    The body is included verbatim — caller is responsible for trailing newline.
    """
    yaml_text = dump_frontmatter(frontmatter)
    parts: list[str] = []
    if yaml_text:
        parts.append("---\n")
        parts.append(yaml_text)
        parts.append("\n---\n")
    # Body — no leading newline if frontmatter present; add one if not
    if body:
        if not yaml_text and not body.startswith("\n"):
            parts.append("")
        parts.append(body)
    return "".join(parts)


def write_concept(
    path: str | Path,
    frontmatter: dict[str, Any],
    body: str,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a concept to `path`. Returns the resolved Path.

    Args:
        path: Destination file path. Parent dirs are created.
        frontmatter: Dict of YAML frontmatter (must include `type`).
        body: Markdown body text.
        overwrite: If False (default), refuses to overwrite an existing file.

    Raises:
        OKFWriteError: If file exists and overwrite=False, or write fails.
        ValueError: If frontmatter is missing required `type` field.
    """
    if "type" not in frontmatter or not frontmatter["type"]:
        raise ValueError(
            "frontmatter must include a non-empty 'type' field (per OKF spec)"
        )

    p = Path(path)
    if p.exists() and not overwrite:
        raise OKFWriteError(f"File already exists: {p} (pass overwrite=True to replace)")

    p.parent.mkdir(parents=True, exist_ok=True)
    text = assemble_concept(frontmatter, body)
    try:
        p.write_text(text, encoding="utf-8")
    except OSError as e:
        raise OKFWriteError(f"Failed to write {p}: {e}") from e
    return p.resolve()


def slugify(text: str) -> str:
    """Convert a title into a safe filename slug.

    >>> slugify("Sales Invoice")
    'sales-invoice'
    >>> slugify("Thai Bank Statement Import")
    'thai-bank-statement-import'
    >>> slugify("Customer (Legacy)")
    'customer-legacy'
    """
    import re
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "untitled"


def concept_path_from_title(bundle_root: str | Path, subdir: str, title: str) -> Path:
    """Build a deterministic concept file path from title.

    >>> concept_path_from_title("/tmp/b", "doctypes", "Sales Invoice")
    PosixPath('/tmp/b/doctypes/sales-invoice.md')
    """
    return Path(bundle_root) / subdir / f"{slugify(title)}.md"
