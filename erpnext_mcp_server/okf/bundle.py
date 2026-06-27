"""Bundle-level operations: index generation, log files, site catalog export, listing.

Provides:
    generate_index(bundle_root) -> Path       (writes index.md)
    generate_log(bundle_root) -> Path         (writes log.md per OKF spec §7)
    record_event(bundle_root, verb, summary, links) -> None  (append event to history)
    list_bundles(okf_root) -> list[dict]       (list bundles under okf_root)
    export_site_catalog(site, bundle_root, ...) -> dict

No Frappe dependency for generate_index, generate_log, record_event, and list_bundles.
export_site_catalog requires Frappe (calls exporter).

Spec reference: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .parser import parse_concept_safe
from .writer import write_concept, slugify


# OKF spec version this implementation targets.
OKF_VERSION = "0.1"

# Per OKF spec §7: log.md is optional but recommended.
# History is stored in .okf_history.json (gitignored) — internal state.
HISTORY_FILENAME = ".okf_history.json"
LOG_FILENAME = "log.md"


def _now_iso() -> str:
    """ISO 8601 UTC datetime string."""
    return datetime.now(timezone.utc).isoformat()


def _load_history(bundle_root: Path) -> list[dict[str, Any]]:
    """Load event history from .okf_history.json. Returns [] if missing/corrupt."""
    history_path = bundle_root / HISTORY_FILENAME
    if not history_path.exists():
        return []
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, OSError):
        return []


def _save_history(bundle_root: Path, history: list[dict[str, Any]]) -> None:
    """Append events to .okf_history.json (atomic write via tmp + rename)."""
    history_path = bundle_root / HISTORY_FILENAME
    bundle_root.mkdir(parents=True, exist_ok=True)
    tmp_path = history_path.with_suffix(".json.tmp")
    try:
        tmp_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(history_path)
    except OSError:
        # Best-effort — log file is non-critical
        pass


def record_event(
    bundle_root: str | Path,
    verb: str,
    summary: str,
    links: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append an event to the bundle's history (used by exporter / re-exports).

    Args:
        bundle_root: Bundle directory
        verb: Action verb used as bold label (e.g. "Update", "Creation", "Initialization")
        summary: Human-readable summary line (no markdown needed)
        links: Optional list of relative concept paths this event touched
        details: Optional structured data (e.g. {"doctypes_exported": 314})

    Returns:
        The event dict that was appended (or {} if write failed)
    """
    event: dict[str, Any] = {
        "timestamp": _now_iso(),
        "verb": verb,
        "summary": summary,
    }
    if links:
        event["links"] = links
    if details:
        event["details"] = details

    root = Path(bundle_root)
    history = _load_history(root)
    history.append(event)
    _save_history(root, history)
    return event


def generate_log(bundle_root: str | Path) -> Path | None:
    """Regenerate the bundle-root log.md from history (per OKF spec §7).

    Format:
        # <Bundle Name> — Directory Update Log

        ## YYYY-MM-DD
        * **Verb**: Summary text [link1] [link2].
        * **Verb**: Summary text [link3].

        ## YYYY-MM-DD (older)
        ...

    Date headings MUST use ISO 8601 YYYY-MM-DD form (spec §7).
    Entries are prose; the leading bold word (**Update**, **Creation**, etc.)
    is a convention, not a requirement.

    Returns the path to log.md, or None if no history yet (nothing to log).
    """
    root = Path(bundle_root)
    history = _load_history(root)
    if not history:
        # No events yet — don't create an empty log
        return None

    # Group events by date (YYYY-MM-DD in UTC)
    by_date: dict[str, list[dict[str, Any]]] = {}
    for event in history:
        ts = event.get("timestamp", "")
        date_str = ts[:10] if ts else "unknown"
        by_date.setdefault(date_str, []).append(event)

    # Sort dates newest first
    sorted_dates = sorted(by_date.keys(), reverse=True)

    lines: list[str] = [
        f"# {root.name} — Directory Update Log",
        "",
        f"This log is auto-generated from `{HISTORY_FILENAME}`.",
        f"OKF spec: §7 (Log Files).",
        "",
    ]

    for date_str in sorted_dates:
        # ISO 8601 date heading (spec mandates this exact format)
        lines.append(f"## {date_str}")
        lines.append("")
        for event in by_date[date_str]:
            verb = event.get("verb", "Update")
            summary = event.get("summary", "")
            links = event.get("links") or []
            details = event.get("details") or {}

            # Format links: each as [Title](relative-path.md)
            link_str = ""
            if links:
                rendered_links = " ".join(f"[`{Path(l).name}`]({l})" for l in links[:10])
                if len(links) > 10:
                    rendered_links += f" ... and {len(links) - 10} more"
                link_str = f" {rendered_links}"

            # Append details in parentheses if present
            detail_str = ""
            if details:
                parts = [f"{k}={v}" for k, v in details.items()]
                detail_str = f" _({', '.join(parts)})_"

            lines.append(f"* **{verb}**: {summary}{link_str}{detail_str}")
        lines.append("")

    log_path = root / LOG_FILENAME
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


def generate_index(bundle_root: str | Path) -> Path:
    """Regenerate the bundle-root index.md from all concepts.

    Per OKF spec, the root index.md may include an `okf_version` field
    (the only place frontmatter is permitted in an index.md).
    Lists every concept with its title, type, tags, and relative path.

    NOTE on spec deviation (spec §6 says index files have NO frontmatter):
    - Google's own example in the 2026 blog uses frontmatter on root index.md
    - Spec §11 explicitly allows `okf_version` on root index.md
    - We follow Google's example: minimal frontmatter on root only (type, okf_version, title, description, generated_by)
    - Sub-directory index.md files (when generated) have NO frontmatter — fully conformant
    """
    root = Path(bundle_root)
    root.mkdir(parents=True, exist_ok=True)

    # Collect all concept files (everything except the root index.md itself)
    md_files = sorted(
        p for p in root.rglob("*.md")
        if p.resolve() != (root / "index.md").resolve() and p.name != LOG_FILENAME
    )

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


def generate_bundle_artifacts(bundle_root: str | Path) -> dict[str, Path]:
    """Generate BOTH index.md and log.md (and any future bundle-level files).

    Convenience function: exporters should call this instead of generate_index()
    directly so they get log.md for free.

    Returns dict with paths to generated files (may omit log.md if no history).
    """
    root = Path(bundle_root)
    idx_path = generate_index(root)
    log_path = generate_log(root)
    out: dict[str, Path] = {"index": idx_path}
    if log_path is not None:
        out["log"] = log_path
    return out


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
                "has_log": (bundle_root / LOG_FILENAME).exists(),
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

    # Record the bulk export event BEFORE running it
    filter_desc = []
    if doctype_filter:
        filter_desc.append(f"name LIKE '{doctype_filter}'")
    if module_filter:
        filter_desc.append(f"module LIKE '{module_filter}'")
    record_event(
        bundle_root=root,
        verb="Update" if _load_history(root) else "Initialization",
        summary=(
            f"Bulk export of DocTypes from {site}"
            + (f" (filter: {', '.join(filter_desc)})" if filter_desc else "")
        ),
        details={
            "site": site,
            "doctype_filter": doctype_filter or "",
            "module_filter": module_filter or "",
            "include_custom": include_custom,
            "include_core": include_core,
        },
    )

    result = export_doctypes(
        site=site,
        bundle_root=root,
        doctype_filter=doctype_filter,
        module_filter=module_filter,
        include_custom=include_custom,
        include_core=include_core,
    )

    # Record the result
    record_event(
        bundle_root=root,
        verb="Update",
        summary=(
            f"Re-exported {result['exported']} DocTypes "
            f"({result['skipped']} skipped, {result['fields_redacted']} fields redacted)"
        ),
        details={
            "exported": result["exported"],
            "skipped": result["skipped"],
            "fields_redacted": result["fields_redacted"],
        },
    )

    # Always regenerate index AND log after export
    artifacts = generate_bundle_artifacts(root)

    return {
        "bundle_path": str(root),
        "site": site,
        "doctypes_exported": result["exported"],
        "doctypes_skipped": result["skipped"],
        "fields_redacted": result["fields_redacted"],
        "index_path": str(artifacts["index"]),
        "log_path": str(artifacts.get("log", "")),
    }
