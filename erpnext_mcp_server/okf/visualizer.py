"""Static HTML visualizer for OKF bundles.

Generates a single self-contained HTML file (with embedded JS via CDN)
that visualizes a bundle as an interactive list + filter UI.

Inspired by Google's `static HTML visualizer` shipped with OKF v0.1
(https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)

CLI usage:
    python -m okf.visualizer --bundle /path/to/bundle --output bundle.html

Programmatic usage:
    from okf.visualizer import generate_html
    generate_html(bundle_root) -> Path
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .parser import parse_concept_safe


# Embedded as a string for portability — no external assets at runtime.
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__BUNDLE_NAME__ — OKF Bundle</title>
<style>
:root {
  --bg: #ffffff;
  --fg: #1a1a1a;
  --muted: #6b7280;
  --border: #e5e7eb;
  --accent: #2563eb;
  --accent-light: #dbeafe;
  --type-bg: #f3f4f6;
  --tag-bg: #ecfdf5;
  --tag-fg: #065f46;
  --warn-bg: #fef3c7;
  --warn-fg: #92400e;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a;
    --fg: #e2e8f0;
    --muted: #94a3b8;
    --border: #334155;
    --accent: #60a5fa;
    --accent-light: #1e3a8a;
    --type-bg: #1e293b;
    --tag-bg: #064e3b;
    --tag-fg: #6ee7b7;
    --warn-bg: #78350f;
    --warn-fg: #fcd34d;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
}
header {
  border-bottom: 1px solid var(--border);
  padding: 24px 32px;
  background: var(--type-bg);
}
header h1 { margin: 0 0 4px; font-size: 24px; }
header .meta { color: var(--muted); font-size: 13px; }
main {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 0;
  min-height: calc(100vh - 80px);
}
aside {
  border-right: 1px solid var(--border);
  padding: 16px;
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}
aside h3 { margin: 8px 0 4px; font-size: 11px; text-transform: uppercase; color: var(--muted); }
aside input, aside select {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 12px;
  background: var(--bg);
  color: var(--fg);
  font-size: 13px;
}
aside .stat { font-size: 12px; color: var(--muted); margin: 8px 0; }
section.content {
  padding: 24px 32px;
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}
article.concept {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
  background: var(--bg);
}
article.concept h2 {
  margin: 0 0 8px;
  font-size: 18px;
}
article.concept .type {
  display: inline-block;
  background: var(--type-bg);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  margin-left: 8px;
  color: var(--muted);
}
article.concept .desc {
  color: var(--muted);
  font-size: 14px;
  margin: 8px 0;
}
article.concept .tags {
  margin: 8px 0;
}
article.concept .tags span {
  display: inline-block;
  background: var(--tag-bg);
  color: var(--tag-fg);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  margin-right: 4px;
}
article.concept .body {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  font-size: 14px;
}
article.concept .body h1,
article.concept .body h2,
article.concept .body h3 { font-size: 16px; margin: 16px 0 8px; }
article.concept .body code { background: var(--type-bg); padding: 1px 4px; border-radius: 3px; font-family: ui-monospace, monospace; font-size: 12px; }
article.concept .body pre { background: var(--type-bg); padding: 8px; border-radius: 6px; overflow-x: auto; }
article.concept .body table { border-collapse: collapse; width: 100%; margin: 8px 0; }
article.concept .body th, article.concept .body td { padding: 6px 8px; border: 1px solid var(--border); text-align: left; }
article.concept .body th { background: var(--type-bg); }
article.concept .body a { color: var(--accent); text-decoration: none; }
article.concept .body a:hover { text-decoration: underline; }
article.concept .meta-row {
  font-size: 11px;
  color: var(--muted);
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed var(--border);
  font-family: ui-monospace, monospace;
}
article.concept .meta-row a { color: var(--muted); }
article.concept .missing-resource { background: var(--warn-bg); color: var(--warn-fg); }
.hidden { display: none; }
.search-row { display: flex; gap: 8px; margin-bottom: 8px; }
.search-row input { flex: 1; }
.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--muted);
}
</style>
</head>
<body>
<header>
  <h1>__BUNDLE_NAME__ <span class="type">__OKF_VERSION__</span></h1>
  <div class="meta">
    Generated __TIMESTAMP__ ·
    __CONCEPT_COUNT__ concepts ·
    __TYPE_COUNT__ types ·
    __TAG_COUNT__ tags
  </div>
</header>
<main>
<aside>
  <h3>Search</h3>
  <div class="search-row">
    <input type="search" id="search" placeholder="Title, description, body..." autofocus>
  </div>

  <h3>Filter by type</h3>
  <select id="typeFilter">
    <option value="">All types</option>__TYPE_OPTIONS__
  </select>

  <h3>Filter by tag</h3>
  <select id="tagFilter">
    <option value="">All tags</option>__TAG_OPTIONS__
  </select>

  <div class="stat" id="visibleCount"></div>
</aside>
<section class="content" id="content">
  <div id="articles"></div>
</section>
</main>

<script>
const CONCEPTS = __CONCEPTS_JSON__;

const typeFilter = document.getElementById("typeFilter");
const tagFilter = document.getElementById("tagFilter");
const state = {
  query: "",
  type: "",
  tag: "",
};

// Dropdowns are pre-rendered server-side; just hook up handlers
document.getElementById("search").addEventListener("input", e => {
  state.query = e.target.value.toLowerCase();
  render();
});
typeFilter.addEventListener("change", e => { state.type = e.target.value; render(); });
tagFilter.addEventListener("change", e => { state.tag = e.target.value; render(); });

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
}

function render() {
  const articles = document.getElementById("articles");
  const visible = CONCEPTS.filter(c => {
    if (state.type && c.type !== state.type) return false;
    if (state.tag && !(c.tags || []).includes(state.tag)) return false;
    if (state.query) {
      const hay = (c.title + " " + (c.description || "") + " " + (c.body || "")).toLowerCase();
      if (!hay.includes(state.query)) return false;
    }
    return true;
  });
  document.getElementById("visibleCount").textContent =
    `Showing ${visible.length} of ${CONCEPTS.length}`;

  if (visible.length === 0) {
    articles.innerHTML = '<div class="empty-state">No concepts match the current filters.</div>';
    return;
  }
  articles.innerHTML = visible.map(c => `
    <article class="concept" id="__ESCAPED_ID__">
      <h2>__ESCAPED_TITLE____TYPE_BADGE__</h2>
      __ESCAPED_DESC__
      __ESCAPED_TAGS__
      __ESCAPED_BODY__
      <div class="meta-row __MISSING_RESOURCE_CLASS__">
        __META_ROW__
      </div>
    </article>
  `).join("");

  // Substitute per-article templates with proper escaping
  articles.innerHTML = visible.map(c => {
    const id = escapeHtml(c.id);
    const title = escapeHtml(c.title || c.id);
    const typeBadge = c.type ? `<span class="type">${escapeHtml(c.type)}</span>` : "";
    const desc = c.description ? `<div class="desc">${escapeHtml(c.description)}</div>` : "";
    const tags = c.tags && c.tags.length
      ? `<div class="tags">${c.tags.map(t => `<span>${escapeHtml(t)}</span>`).join("")}</div>`
      : "";
    const body = c.body ? `<div class="body">${c.body_html}</div>` : "";
    const missingClass = c.resource ? "" : "missing-resource";
    const metaRow = c.resource
      ? `<strong>resource:</strong> <a href="${escapeHtml(c.resource)}">${escapeHtml(c.resource)}</a>`
      : "<strong>resource:</strong> (none — abstract concept)";
    const ts = c.timestamp ? ` · <strong>timestamp:</strong> ${escapeHtml(c.timestamp)}` : "";
    const anchor = `<a href="#${id}">#${id}</a>`;
    return `
    <article class="concept" id="${id}">
      <h2>${title}${typeBadge}</h2>
      ${desc}
      ${tags}
      ${body}
      <div class="meta-row ${missingClass}">
        ${metaRow}${ts} · ${anchor}
      </div>
    </article>`;
  }).join("");
}

render();
</script>
</body>
</html>"""


def _escape(s: str) -> str:
    """HTML-escape a string for safe interpolation."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _render_markdown_to_html(md: str) -> str:
    """Convert basic Markdown to HTML for the visualizer.

    Supports: headings (# ## ###), bold (**), italic (*), code (`),
    preformatted blocks (```), tables (|...|), links [text](url).
    NOT a full Markdown renderer — just enough for OKF concepts.

    SECURITY: HTML special chars in body text are escaped FIRST, before
    applying markdown. This prevents XSS — even if a concept body
    contains <script>, it renders as literal text, not executable HTML.
    """
    import re

    if not md:
        return ""

    # Step 1: Stash code blocks, inline code, tables, and links
    # (we don't escape their content; that's verbatim)
    placeholders: list[str] = []

    def _stash(match: "re.Match[str]") -> str:
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"\x00PH{idx}\x00"

    md = re.sub(r"```(\w*)\n(.*?)\n```", _stash, md, flags=re.DOTALL)
    md = re.sub(r"`([^`]+)`", _stash, md)
    md = re.sub(r"(?:^\|.+\|$\n?){2,}", _stash, md, flags=re.MULTILINE)
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _stash, md)

    # Step 2: HTML-escape remaining body text (no markdown left to confuse)
    md = _escape(md)

    # Step 3: Apply markdown transformations on escaped text
    html = md
    html = re.sub(r"^###### (.+)$", r"<h6>\1</h6>", html, flags=re.MULTILINE)
    html = re.sub(r"^##### (.+)$", r"<h5>\1</h5>", html, flags=re.MULTILINE)
    html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", html)

    # Paragraphs (double newline)
    parts = html.split("\n\n")
    out_parts = []
    for p in parts:
        if p.startswith("<"):
            out_parts.append(p)
        else:
            out_parts.append("<p>" + p.replace("\n", "<br>") + "</p>")
    html = "\n".join(out_parts)

    # Step 4: Restore stashed content (now rendered to HTML)
    def _render_table(table_md: str) -> str:
        rows = table_md.strip().split("\n")
        if len(rows) < 2:
            return table_md
        header = [c.strip() for c in rows[0].strip("|").split("|")]
        body_rows = []
        for row in rows[2:]:
            cells = [c.strip() for c in row.strip("|").split("|")]
            body_rows.append(cells)
        out = "<table><thead><tr>"
        for h in header:
            out += f"<th>{_escape(h)}</th>"
        out += "</tr></thead><tbody>"
        for row in body_rows:
            out += "<tr>"
            for c in row:
                out += f"<td>{_escape(c)}</td>"
            out += "</tr>"
        out += "</tbody></table>"
        return out

    def _restore(m: "re.Match[str]") -> str:
        idx = int(m.group(1))
        original = placeholders[idx]
        if original.startswith("```"):
            lang_match = re.match(r"```(\w*)\n(.*?)\n```", original, re.DOTALL)
            lang = lang_match.group(1) if lang_match else ""
            code = lang_match.group(2) if lang_match else ""
            return f'<pre><code class="language-{_escape(lang)}">{_escape(code)}</code></pre>'
        if original.startswith("|"):
            return _render_table(original)
        if original.startswith("`"):
            inner = original[1:-1]
            return f"<code>{_escape(inner)}</code>"
        if original.startswith("["):
            link_match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", original)
            if link_match:
                text, url = link_match.group(1), link_match.group(2)
                return f'<a href="{_escape(url)}">{_escape(text)}</a>'
        return _escape(original)

    html = re.sub(r"\x00PH(\d+)\x00", _restore, html)
    return html


def generate_html(
    bundle_root: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Generate a self-contained HTML file visualizing the bundle.

    Args:
        bundle_root: Path to the OKF bundle directory.
        output_path: Where to write the HTML. Defaults to `<bundle_root>/index.html`.

    Returns:
        Path to the generated HTML file.

    The HTML file:
      - Embeds all concept data as JSON (no server needed)
      - Loads no external assets (system fonts only)
      - Supports search, filter by type, filter by tag
      - Renders concept body as HTML (basic Markdown subset)
      - Server-side rendered dropdown options (no JS dependency for initial render)
    """
    root = Path(bundle_root)
    if not root.exists():
        raise FileNotFoundError(f"Bundle root does not exist: {root}")

    # Collect all concept files (skip index.md — it's the bundle's own index)
    md_files = sorted(p for p in root.rglob("*.md") if p.name == "concept.md" or True)
    md_files = [p for p in md_files if p.name not in ("index.md", "log.md")]

    concepts: list[dict[str, Any]] = []
    all_types: set[str] = set()
    all_tags: set[str] = set()

    for md in md_files:
        rel = md.relative_to(root).as_posix()
        parsed = parse_concept_safe(md)
        if parsed is None:
            continue
        fm = parsed.get("frontmatter") or {}
        body_md = parsed.get("body") or ""
        concept = {
            "id": rel.replace("/", "__").replace(".md", ""),
            "path": rel,
            "title": fm.get("title") or md.stem.replace("-", " ").title(),
            "type": fm.get("type"),
            "description": fm.get("description") or "",
            "tags": fm.get("tags") or [],
            "resource": fm.get("resource"),
            "timestamp": fm.get("timestamp"),
            "body": body_md,
            "body_html": _render_markdown_to_html(body_md),
        }
        concepts.append(concept)
        if concept["type"]:
            all_types.add(concept["type"])
        for t in concept["tags"]:
            all_tags.add(t)

    # Determine output path
    if output_path is None:
        output_path = root / "index.html"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Render template substitutions
    html = HTML_TEMPLATE
    html = html.replace("__BUNDLE_NAME__", _escape(root.name))
    html = html.replace("__OKF_VERSION__", "OKF v0.1")
    html = html.replace(
        "__TIMESTAMP__", datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    html = html.replace("__CONCEPT_COUNT__", str(len(concepts)))
    html = html.replace("__TYPE_COUNT__", str(len(all_types)))
    html = html.replace("__TAG_COUNT__", str(len(all_tags)))
    html = html.replace("__CONCEPTS_JSON__", json.dumps(concepts, ensure_ascii=False))

    # Pre-render type + tag dropdown options (instant first paint, no JS delay)
    type_options = "".join(
        f'<option value="{_escape(t)}">{_escape(t)}</option>'
        for t in sorted(all_types)
    )
    tag_options = "".join(
        f'<option value="{_escape(t)}">{_escape(t)}</option>'
        for t in sorted(all_tags)
    )
    html = html.replace("__TYPE_OPTIONS__", type_options)
    html = html.replace("__TAG_OPTIONS__", tag_options)

    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    """CLI entry point: `python -m okf.visualizer --bundle <path> --output <path>`"""
    parser = argparse.ArgumentParser(
        description="Generate a self-contained HTML visualizer for an OKF bundle"
    )
    parser.add_argument(
        "--bundle", required=True, help="Path to the OKF bundle directory"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output HTML path (default: <bundle>/index.html)",
    )
    args = parser.parse_args()
    out = generate_html(args.bundle, args.output)
    size_kb = out.stat().st_size / 1024
    print(f"✅ Generated: {out}")
    print(f"   Size: {size_kb:.1f} KB")
    print(f"   Concepts: open in browser to view")


if __name__ == "__main__":
    main()
