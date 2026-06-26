"""Frappe DocType → OKF concept exporter.

Reads DocType metadata via Frappe's meta API and writes one Markdown concept per DocType.
Handles child tables as internal links, redacts secret fields, and includes a structured
"Key Fields" table for easy scanning.

Requires Frappe to be initialized (bench context).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .redaction import is_secret_field, redact_field_definition
from .writer import concept_path_from_title, write_concept


def _require_frappe():
    """Lazy import of frappe — gives a clear error if called outside bench context."""
    try:
        import frappe  # noqa: F401
        return frappe
    except ImportError as e:
        raise RuntimeError(
            "frappe is required for exporter functions. Run via `bench execute` "
            "or in a context where Frappe is initialized (e.g. bench console)."
        ) from e


def _collect_fields(doctype_name: str, frappe) -> list[dict[str, Any]]:
    """Return redacted field definitions for a DocType.

    Each entry: {fieldname, fieldtype, options (if not secret), _redacted (bool)}.
    """
    meta = frappe.get_meta(doctype_name)
    fields = []
    for f in meta.fields:
        fields.append(redact_field_definition(f.fieldname, f.fieldtype, getattr(f, "options", None)))
    return fields


def _collect_child_tables(doctype_name: str, frappe) -> list[str]:
    """Return names of child tables (istable=1) referenced by this DocType."""
    meta = frappe.get_meta(doctype_name)
    children = []
    for f in meta.fields:
        if f.fieldtype == "Table" and getattr(f, "options", None):
            children.append(f.options)
    return children


def _build_body(
    doctype_name: str,
    fields: list[dict[str, Any]],
    child_tables: list[str],
    site: str,
    app: str | None,
    module: str | None,
    description: str | None,
) -> str:
    """Build the Markdown body for a DocType concept."""
    parts: list[str] = []

    parts.append(f"# {doctype_name}")
    parts.append("")
    if description:
        parts.append(description)
        parts.append("")
    parts.append(f"_Site_: `{site}`")
    if app:
        parts.append(f"_App_: `{app}`")
    if module:
        parts.append(f"_Module_: `{module}`")
    parts.append("")

    # Key Fields table
    if fields:
        parts.append("## Key Fields")
        parts.append("")
        parts.append("| Field | Type | Options |")
        parts.append("|---|---|---|")
        for f in fields[:50]:   # cap at 50 to keep concepts readable
            opts = f.get("options") or ""
            if f.get("_redacted"):
                opts = "***REDACTED***"
            elif isinstance(opts, str) and len(opts) > 60:
                opts = opts[:57] + "..."
            flag = " 🔒" if f.get("_redacted") else ""
            parts.append(f"| `{f['fieldname']}` | {f['fieldtype']} | {opts} |{flag}".rstrip("|"))
        parts.append("")
        if len(fields) > 50:
            parts.append(f"_... and {len(fields) - 50} more fields. See Frappe meta for full list._")
            parts.append("")

    # Child Tables
    if child_tables:
        parts.append("## Child Tables")
        parts.append("")
        for ct in child_tables:
            slug = ct.lower().replace(" ", "-")
            parts.append(f"- [{ct}](../doctypes/{slug}.md)")
        parts.append("")

    # Related Code (best-effort: look for app + module)
    if app:
        parts.append("## Related")
        parts.append("")
        parts.append(f"- Frappe Meta: `frappe://{site}/doctype/{doctype_name}`")
        parts.append(f"- App source: typically under `apps/{app}/{app}/doctype/{doctype_name.lower().replace(' ', '_')}/`")
        parts.append("")

    parts.append("## Agent Notes")
    parts.append("")
    parts.append("- This concept was auto-generated from Frappe metadata.")
    parts.append("- Field options that may contain secrets have been redacted (🔒).")
    parts.append("- For runtime document data, use `get_document` MCP tool — not OKF.")
    parts.append("")

    return "\n".join(parts)


def export_doctype(
    doctype_name: str,
    bundle_root: str | Path,
    site: str,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Export a single DocType as an OKF concept.

    Returns:
        {
            "path": str,          # absolute path of written .md
            "concept": str,       # doctype name (sanitized)
            "fields_redacted": int,
            "fields_total": int,
            "child_tables": int,
        }
    """
    frappe = _require_frappe()

    # Ensure the right site is bound
    if site and frappe.local.site != site:
        frappe.init_site(site)
        frappe.connect()

    # Fetch meta
    if not frappe.db.exists("DocType", doctype_name):
        raise ValueError(f"DocType does not exist: {doctype_name}")

    meta = frappe.get_meta(doctype_name)
    fields = _collect_fields(doctype_name, frappe)
    child_tables = _collect_child_tables(doctype_name, frappe)

    fields_redacted = sum(1 for f in fields if f.get("_redacted"))

    # Determine app + module
    app = getattr(meta, "app", None) or getattr(meta, "module", None) or None
    module = getattr(meta, "module", None) or None
    description = getattr(meta, "description", None) or None

    # Build frontmatter
    from datetime import datetime, timezone
    frontmatter = {
        "type": "Frappe DocType",
        "title": doctype_name,
        "description": description or f"Frappe DocType: {doctype_name}",
        "resource": f"frappe://{site}/doctype/{doctype_name}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tags": _make_tags(meta, app, module),
    }
    if app:
        frontmatter["app"] = app
    if module:
        frontmatter["module"] = module

    # Build body
    body = _build_body(doctype_name, fields, child_tables, site, app, module, description)

    # Write
    path = concept_path_from_title(bundle_root, "doctypes", doctype_name)
    write_concept(path, frontmatter, body, overwrite=overwrite)

    return {
        "path": str(path),
        "concept": doctype_name,
        "fields_redacted": fields_redacted,
        "fields_total": len(fields),
        "child_tables": len(child_tables),
    }


def export_doctypes(
    site: str,
    bundle_root: str | Path,
    *,
    doctype_filter: str | None = None,
    module_filter: str | None = None,
    include_custom: bool = True,
    include_core: bool = False,
    overwrite: bool = False,
    limit: int | None = None,
) -> dict[str, int]:
    """Export many DocTypes in bulk.

    Args:
        doctype_filter: SQL LIKE filter for DocType.name (e.g. "Thai Bank %")
        module_filter: SQL LIKE filter for DocType.module (e.g. "Thai %")
        include_custom: Include custom DocTypes (modules NOT in core list)
        include_core: Include ERPNext/Frappe core DocTypes (modules in core list)
        overwrite: Overwrite existing concept files
        limit: Cap on number of DocTypes exported (None = all)

    Returns:
        {"exported": int, "skipped": int, "fields_redacted": int, "total_seen": int}
    """
    frappe = _require_frappe()

    if site and frappe.local.site != site:
        frappe.init_site(site)
        frappe.connect()

    # Core modules — used to identify "custom" vs "core" DocTypes
    # (Frappe v16 doesn't populate `app` or `custom` columns reliably)
    CORE_MODULES = (
        "Core", "Website", "Email", "Desk", "Social", "Automation",
        "Printing", "Integrations", "Contacts", "Telephony", "Geo",
        "Custom", "Workflow",
        # ERPNext modules
        "Accounts", "Selling", "Buying", "Stock", "Manufacturing",
        "Projects", "HR", "Payroll", "Assets", "Maintenance", "Quality",
        "Production", "Retail", "School", "Healthcare", "Hospitality",
        "Loans", "Taxes", "Support", "CRM", "Education",
        # System
        "System", "Customize Form", "Build", "Permissions", "Settings",
    )
    core_list = ", ".join(f"'{m}'" for m in CORE_MODULES)

    where_parts = ["`name` NOT LIKE ' %'"]
    # Exclude system internals
    where_parts.append("""`name` NOT IN (
        'DocField', 'DocPerm', 'DocType Action', 'DocType Link',
        'DocType State', 'Has Role', 'Page', 'Report', 'Report Column',
        'Report Filter', 'Report Graph', 'Number Card', 'Dashboard Chart',
        'Dashboard Chart Field', 'Custom Field', 'Customize Form Field',
        'Customize Form', 'Workspace', 'Workspace Link', 'Workspace Chart',
        'Workspace Number Card', 'Workspace Shortcut', 'Workspace Sidebar'
    )""")
    # Exclude virtual DocTypes (cannot export metadata meaningfully)
    where_parts.append("`is_virtual` = 0")
    # Hide chat thread / internal helpers
    where_parts.append("`name` NOT IN ('Chat Room', 'Chat Message', 'Chat Profile', 'Chat Token', 'Chat Session', 'Communication')")

    # Apply custom vs core filter based on module
    if include_custom and not include_core:
        where_parts.append(f"`module` NOT IN ({core_list})")
    elif include_core and not include_custom:
        where_parts.append(f"`module` IN ({core_list})")
    # If both or neither, include everything

    if doctype_filter:
        # Escape LIKE wildcards in user input
        safe = doctype_filter.replace("'", "''")
        where_parts.append(f"`name` LIKE '{safe}'")

    if module_filter:
        safe = module_filter.replace("'", "''")
        where_parts.append(f"`module` LIKE '{safe}'")

    where_sql = " AND ".join(where_parts)
    sql = f"SELECT `name`, `module` FROM `tabDocType` WHERE {where_sql} ORDER BY `module`, `name`"
    if limit:
        sql += f" LIMIT {int(limit)}"

    doctypes = frappe.db.sql(sql, as_dict=True)
    total = len(doctypes)

    exported = 0
    skipped = 0
    fields_redacted_total = 0

    for row in doctypes:
        dt_name = row["name"]
        try:
            result = export_doctype(dt_name, bundle_root, site, overwrite=overwrite)
            exported += 1
            fields_redacted_total += result.get("fields_redacted", 0)
        except FileExistsError:
            skipped += 1
        except Exception as e:
            skipped += 1
            # Log but don't crash — exporter should be resilient
            import logging
            logging.getLogger(__name__).warning(f"Skipped {dt_name}: {e}")

    return {
        "exported": exported,
        "skipped": skipped,
        "total_seen": total,
        "fields_redacted": fields_redacted_total,
    }


def _make_tags(meta, app: str | None, module: str | None) -> list[str]:
    """Build a tags list from DocType metadata.

    Avoids duplicating when `app` and `module` are the same string.
    """
    tags = []
    app_slug = app.lower().replace(" ", "-") if app else None
    module_slug = module.lower().replace(" ", "-") if module else None
    if app_slug:
        tags.append(app_slug)
    if module_slug and module_slug != app_slug:
        tags.append(module_slug)
    if getattr(meta, "is_virtual", 0):
        tags.append("virtual")
    if getattr(meta, "istable", 0):
        tags.append("child-table")
    if getattr(meta, "track_changes", 0):
        tags.append("track-changes")
    return tags[:8]
