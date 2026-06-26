"""Bundle-level operations: index generation, site catalog export, listing.

Provides:
    generate_index(bundle_root) -> Path   (writes index.md)
    list_bundles(okf_root) -> list[dict]   (list bundles under okf_root)
    export_site_catalog(site, bundle_root, ...) -> dict

No Frappe dependency for generate_index and list_bundles.
export_site_catalog requires Frappe (calls exporter).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .parser import parse_concept_safe
from .writer import write_concept, slugify


# OKF spec version this implementation targets.
OKF_VERSION = "0.1"


def generate_index(bundle_root: str | Path) -> Path:
    """Regenerate the bundle-root index.md from all concepts.

    Per OKF spec, the root index.md may include an `okf_version` field
    (the only place frontmatter is permitted in an index.md).
    Lists every concept with its title, type, tags, and relative path.
    """
    root = Path(bundle_root)
    root.mkdir(parents=True, exist_ok=True)

    # Collect all concept files (everything except the root index.md itself)
    md_files = sorted(p for p in root.rglob("*.md") if p.resolve() != (root / "index.md").resolve())

    # Group by top-level subdir for readability
    by_section: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for md in md_files:
        try:
            rel = md.relative_to(root)
        except ValueError:
            continue
        section = rel.parts[0] if len(rel.parts) > 1 else "_root"
        parsed = parse_concept_safe(md)
        if parsed is None:
            continue
        by_section.setdefault(section, []).append((rel, parsed.get("frontmatter") or {}))

    # Build index body
    lines: list[str] = [
        f"# {root.name} — OKF Bundle",
        "",
        f"This bundle was auto-generated. OKF version: `{OKF_VERSION}`.",
        f"Total concepts: {sum(len(v) for v in by_section.values())}.",
        "",
    ]

    if not by_section:
        lines.append("_No concepts yet. Use `okf_export_doctype` or `okf_export_site_catalog` to populate._")
        lines.append("")

    for section in sorted(by_section.keys()):
        lines.append(f"## {section}")
        lines.append("")
        # Sort within section by title (or filename fallback)
        items = sorted(
            by_section[section],
            key=lambda kv: (kv[1].get("title") or kv[0].stem).lower(),
        )
        for rel, fm in items:
            title = fm.get("title") or rel.stem.replace("-", " ").replace("_", " ").title()
            ctype = fm.get("type") or "Unknown"
            desc = fm.get("description") or ""
            tags = fm.get("tags") or []
            tag_str = " ".join(f"`{t}`" for t in tags[:6]) if isinstance(tags, list) else ""
            lines.append(f"- [{title}]({rel.as_posix()}) — *{ctype}*")
            if desc:
                lines.append(f"  - {desc}")
            if tag_str:
                lines.append(f"  - Tags: {tag_str}")
        lines.append("")

    frontmatter = {
        "type": "OKF Bundle Index",
        "okf_version": OKF_VERSION,
        "title": root.name,
        "description": f"Auto-generated OKF bundle index ({sum(len(v) for v in by_section.values())} concepts)",
        "generated_by": "erpnext_mcp_server/okf",
    }
    body = "\n".join(lines)
    return write_concept(root / "index.md", frontmatter, body, overwrite=True)


def list_bundles(okf_root: str | Path) -> list[dict[str, Any]]:
    """List all bundle directories under okf_root.

    A bundle is any directory containing an index.md.
    """
    root = Path(okf_root)
    if not root.exists():
        return []
    bundles = []
    for idx in root.rglob("index.md"):
        # Only count as a bundle if this index.md has the okf_version marker
        parsed = parse_concept_safe(idx)
        if parsed and "okf_version" in (parsed.get("frontmatter") or {}):
            bundle_root = idx.parent
            bundles.append({
                "name": bundle_root.name,
                "path": str(bundle_root),
                "concept_count": sum(1 for _ in bundle_root.rglob("*.md")) - 1,  # exclude root index.md
                "okf_version": parsed["frontmatter"].get("okf_version"),
            })
    return sorted(bundles, key=lambda b: b["name"])


def export_site_catalog(
    site: str,
    bundle_root: str | Path,
    *,
    doctype_filter: str | None = None,
    module_filter: str | None = None,
    include_custom: bool = True,
    include_core: bool = False,
) -> dict[str, Any]:
    """Export all matching DocTypes from a Frappe site as OKF concepts.

    Wraps exporter.export_doctypes() with bundle-level bookkeeping.

    Returns:
        {
            "bundle_path": str,
            "site": str,
            "doctypes_exported": int,
            "doctypes_skipped": int,
            "fields_redacted": int,
            "index_path": str,
        }
    """
    # Lazy import — exporter needs Frappe
    from .exporter import export_doctypes

    root = Path(bundle_root)
    root.mkdir(parents=True, exist_ok=True)

    result = export_doctypes(
        site=site,
        bundle_root=root,
        doctype_filter=doctype_filter,
        module_filter=module_filter,
        include_custom=include_custom,
        include_core=include_core,
    )

    # Always regenerate index after export
    idx = generate_index(root)

    return {
        "bundle_path": str(root),
        "site": site,
        "doctypes_exported": result.get("exported", 0),
        "doctypes_skipped": result.get("skipped", 0),
        "fields_redacted": result.get("fields_redacted", 0),
        "index_path": str(idx),
    }
