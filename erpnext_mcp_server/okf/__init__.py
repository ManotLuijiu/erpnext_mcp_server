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
    bundle.generate_log(bundle_root) -> Path           # NEW: spec §7
    bundle.record_event(bundle_root, verb, summary, links, details) -> dict
    bundle.generate_bundle_artifacts(bundle_root) -> dict  # index + log
    bundle.export_site_catalog(site, bundle_root) -> dict
    skills_exporter.export_skills(skills_root, bundle_root, subdir="skills") -> list[Path]
    visualizer.generate_html(bundle_root) -> Path    # NEW: static HTML viewer

Conformance notes (vs Google OKF spec v0.1):
  - ✅ Required `type` field enforced
  - ✅ Recommended fields: title, description, tags
  - ⚠️ `resource` is OPTIONAL (spec §4.1) — we soft-warn if missing
  - ✅ Bundle-root index.md auto-generated
  - ⚠️ Root index.md includes minimal frontmatter (matches Google's own
    example; spec §11 explicitly allows okf_version on root)
  - ✅ Sub-dir index.md files have NO frontmatter (fully conformant §6)
  - ✅ Cross-concept markdown links (graph structure)
  - ✅ log.md auto-generated per spec §7 (date-grouped entries)
  - ✅ Permissive consumer (MUST NOT reject unknown types per §9)
  - ✅ Git-versionable, no proprietary tooling

No Frappe dependency required for core (writer/parser/validator/redaction/bundle).
Frappe only needed for exporter.export_doctype.
"""

__version__ = "0.1.0"
