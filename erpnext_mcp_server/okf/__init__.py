"""OKF (Open Knowledge Format) layer for ERPNext MCP Server.

Implements a minimal subset of the Open Knowledge Format spec
(https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
for exporting Frappe DocTypes, Reports, Workflows, Custom Fields, and Claude Skills
as versionable Markdown concepts.

Public API:
    writer.write_concept(path, frontmatter, body) -> Path
    parser.parse_concept(text) -> {frontmatter, body}
    parser.parse_file(path) -> {frontmatter, body}
    validator.is_safe_path(bundle_root, requested) -> bool
    validator.validate_bundle(bundle_root) -> {valid, errors, warnings}
    redaction.is_secret_field(name) -> bool
    redaction.redact_value(value) -> "***REDACTED***"
    exporter.export_doctype(doctype, bundle_root, site) -> Path
    search.list_concepts(bundle_root, type=None, tag=None) -> list[dict]
    search.get_concept(bundle_root, path) -> dict
    search.search_bundle(bundle_root, query, limit=20) -> list[dict]
    bundle.generate_index(bundle_root) -> Path
    bundle.export_site_catalog(site, bundle_root) -> dict
    skills_exporter.export_skills(skills_root, bundle_root, subdir="skills") -> list[Path]

No Frappe dependency required for core (writer/parser/validator/redaction).
Frappe only needed for exporter.export_doctype.
"""

__version__ = "0.1.0"
