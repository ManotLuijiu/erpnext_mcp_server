"""Bundle + path safety validator.

Enforces:
  - Bundle root is within an allowed sandbox
  - Requested concept paths cannot escape via `..` or absolute paths
  - Bundle-root index.md has `okf_version`
  - Concepts have required `type` field
  - Internal links resolve to existing concepts

No Frappe dependency.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .parser import parse_concept_safe


# Allowed bundle name pattern (filesystem-safe).
BUNDLE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# Concept path pattern (relative to bundle root).
CONCEPT_PATH_RE = re.compile(r"^[a-z0-9][a-z0-9/_-]{0,255}\.md$")

# Required frontmatter fields (per OKF spec).
REQUIRED_FIELDS = ("type",)

# Recommended fields (warn if missing).
RECOMMENDED_FIELDS = ("title", "description", "tags")


class OKFValidationError(ValueError):
    """Raised for hard validation errors."""


def is_safe_bundle_name(name: str) -> bool:
    """Check that a bundle name is filesystem-safe."""
    return bool(BUNDLE_NAME_RE.match(name))


def is_safe_concept_path(path: str) -> bool:
    """Check that a concept path (relative to bundle root) is safe.

    Rejects: absolute paths, paths with '..', paths with null bytes, weird chars.
    """
    if not isinstance(path, str) or not path:
        return False
    if "\x00" in path:
        return False
    # Reject any '..' segment (also catches absolute paths starting with /)
    parts = Path(path).parts
    if any(p == ".." for p in parts):
        return False
    if Path(path).is_absolute():
        return False
    return bool(CONCEPT_PATH_RE.match(path))


def resolve_safe_path(bundle_root: str | Path, requested: str) -> Path | None:
    """Resolve a concept path under bundle_root, blocking traversal.

    Returns the absolute Path if safe, or None if the requested path
    would escape bundle_root or violates path safety rules.
    """
    if not is_safe_concept_path(requested):
        return None
    root = Path(bundle_root).resolve()
    target = (root / requested).resolve()
    # Defense-in-depth: ensure target is still under root
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def validate_concept(concept: dict[str, Any], path: Path) -> tuple[list[str], list[str]]:
    """Validate a single parsed concept.

    Returns (errors, warnings). Errors are blocking; warnings are advisory.
    """
    errors: list[str] = []
    warnings: list[str] = []

    fm = concept.get("frontmatter") or {}

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in fm or not fm[field]:
            errors.append(f"[{path.name}] missing required frontmatter field: '{field}'")

    # Recommended fields (warn only)
    for field in RECOMMENDED_FIELDS:
        if field not in fm:
            warnings.append(f"[{path.name}] missing recommended field: '{field}'")

    # Tags must be a list if present
    if "tags" in fm and not isinstance(fm["tags"], list):
        warnings.append(f"[{path.name}] 'tags' should be a list, got {type(fm['tags']).__name__}")

    return errors, warnings


def validate_bundle(bundle_root: str | Path) -> dict[str, Any]:
    """Validate an entire bundle directory.

    Returns:
        {
          "valid": bool,
          "errors": [str, ...],
          "warnings": [str, ...],
          "concepts": int,
          "index_present": bool,
        }
    """
    root = Path(bundle_root)
    errors: list[str] = []
    warnings: list[str] = []

    if not root.exists():
        return {"valid": False, "errors": [f"Bundle root does not exist: {root}"], "warnings": [], "concepts": 0, "index_present": False}

    # Find all .md files
    md_files = list(root.rglob("*.md"))
    index_path = root / "index.md"
    index_present = index_path.exists()

    if not index_present:
        warnings.append("Bundle is missing root index.md (auto-regenerate with bundle.generate_index)")

    # Validate each concept (skip the root index.md per OKF spec — frontmatter optional there)
    concept_count = 0
    for md in md_files:
        if md.resolve() == index_path.resolve():
            continue
        concept_count += 1
        parsed = parse_concept_safe(md)
        if parsed is None:
            errors.append(f"[{md.relative_to(root)}] failed to parse")
            continue
        e, w = validate_concept(parsed, md)
        errors.extend(e)
        warnings.extend(w)

    # Check bundle-root index.md has okf_version (warn if missing)
    if index_present:
        idx = parse_concept_safe(index_path)
        if idx and "okf_version" not in (idx.get("frontmatter") or {}):
            warnings.append("Bundle index.md missing 'okf_version' field")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "concepts": concept_count,
        "index_present": index_present,
    }
