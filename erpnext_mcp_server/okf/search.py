"""Bundle read + search.

Frontmatter-aware text search (no embeddings in v1).

Public API:
    list_concepts(bundle_root, type=None, tag=None) -> list[dict]
    get_concept(bundle_root, path) -> dict   (full text + parsed frontmatter)
    search_bundle(bundle_root, query, limit=20) -> list[dict]
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .parser import parse_concept_safe
from .validator import is_safe_concept_path, resolve_safe_path


def _iter_concepts(bundle_root: Path):
    """Yield (rel_path, parsed_dict) for every concept under bundle_root.

    Skips the bundle-root index.md.
    """
    idx_path = (bundle_root / "index.md").resolve()
    for md in sorted(bundle_root.rglob("*.md")):
        if md.resolve() == idx_path:
            continue
        rel = md.relative_to(bundle_root)
        parsed = parse_concept_safe(md)
        if parsed is None:
            continue
        yield rel, parsed


def list_concepts(
    bundle_root: str | Path,
    *,
    type: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    """List concepts in a bundle, optionally filtered by type/tag.

    Returns: list of {"path", "title", "type", "tags", "description"}
    """
    root = Path(bundle_root)
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for rel, parsed in _iter_concepts(root):
        fm = parsed.get("frontmatter") or {}
        if type and fm.get("type") != type:
            continue
        if tag:
            tags = fm.get("tags") or []
            if not isinstance(tags, list) or tag not in tags:
                continue
        out.append({
            "path": rel.as_posix(),
            "title": fm.get("title") or rel.stem,
            "type": fm.get("type"),
            "tags": fm.get("tags") or [],
            "description": fm.get("description") or "",
        })
    return out


def get_concept(bundle_root: str | Path, concept_path: str) -> dict[str, Any] | None:
    """Read a single concept by relative path.

    Returns None if the path is unsafe or doesn't exist.
    Result includes: {"path", "frontmatter", "body", "raw"}.
    """
    target = resolve_safe_path(bundle_root, concept_path)
    if target is None or not target.exists():
        return None
    parsed = parse_concept_safe(target)
    if parsed is None:
        return None
    return {
        "path": concept_path,
        "frontmatter": parsed.get("frontmatter") or {},
        "body": parsed.get("body") or "",
        "raw": target.read_text(encoding="utf-8"),
    }


# ---- search ----

def _make_snippet(text: str, query: str, window: int = 120) -> str:
    """Extract a snippet around the first match of `query` in `text`."""
    text_l = text.lower()
    q_l = query.lower()
    idx = text_l.find(q_l)
    if idx < 0:
        return text[:window].strip()
    start = max(0, idx - window // 2)
    end = min(len(text), idx + len(query) + window // 2)
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def search_bundle(
    bundle_root: str | Path,
    query: str,
    *,
    limit: int = 20,
    type: str | None = None,
) -> list[dict[str, Any]]:
    """Text search across concepts (frontmatter + body).

    Scoring:
      - frontmatter title match: +10
      - frontmatter type match: +5
      - frontmatter tag match: +5
      - frontmatter description match: +3
      - body match: +1 per occurrence (capped)

    Returns: list of {"path", "title", "type", "snippet", "score"}
    """
    if not query or not query.strip():
        return []
    if limit > 100:
        limit = 100

    root = Path(bundle_root)
    if not root.exists():
        return []

    q_lower = query.lower()
    results: list[dict[str, Any]] = []

    for rel, parsed in _iter_concepts(root):
        fm = parsed.get("frontmatter") or {}
        body = parsed.get("body") or ""

        # Filter by type first
        if type and fm.get("type") != type:
            continue

        score = 0
        # Title match
        title = fm.get("title") or rel.stem
        if q_lower in title.lower():
            score += 10
        # Type match
        if q_lower in (fm.get("type") or "").lower():
            score += 5
        # Tag match
        tags = fm.get("tags") or []
        if isinstance(tags, list) and any(q_lower in str(t).lower() for t in tags):
            score += 5
        # Description match
        if q_lower in (fm.get("description") or "").lower():
            score += 3
        # Body match (count occurrences, cap at 3)
        body_l = body.lower()
        if q_lower in body_l:
            occurrences = body_l.count(q_lower)
            score += min(occurrences, 3)

        if score > 0:
            snippet = _make_snippet(body if body else title, query)
            results.append({
                "path": rel.as_posix(),
                "title": title,
                "type": fm.get("type"),
                "snippet": snippet,
                "score": score,
            })

    # Sort by score desc, then path
    results.sort(key=lambda r: (-r["score"], r["path"]))
    return results[:limit]


def recommend_skill(
    bundle_root: str | Path,
    task_description: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Recommend Claude Skills matching a task description.

    Just a thin wrapper over search_bundle() with type="Claude Skill".
    """
    return search_bundle(bundle_root, task_description, limit=limit, type="Claude Skill")
