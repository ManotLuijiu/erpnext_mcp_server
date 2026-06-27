"""Tests for visualizer.py — static HTML generator."""

import re
from pathlib import Path

import pytest

from erpnext_mcp_server.okf.visualizer import (
    generate_html,
    _render_markdown_to_html,
    _escape,
)
from erpnext_mcp_server.okf.writer import write_concept


@pytest.fixture
def sample_bundle(tmp_path):
    """Create a small bundle for visualizer testing."""
    (tmp_path / "doctypes").mkdir()
    (tmp_path / "skills").mkdir()
    write_concept(
        tmp_path / "doctypes" / "sales-invoice.md",
        {
            "type": "Frappe DocType",
            "title": "Sales Invoice",
            "description": "Standard sales invoice document",
            "tags": ["billing", "erpnext"],
            "resource": "frappe://test/doctype/Sales Invoice",
        },
        "# Sales Invoice\n\nThis is the body with **bold** text and [a link](./customer.md).",
    )
    write_concept(
        tmp_path / "skills" / "frappe-css.md",
        {
            "type": "Claude Skill",
            "title": "Frappe CSS Layout",
            "tags": ["css"],
        },
        "# Frappe CSS\n\nUse `currentColor` for theme-aware styling.",
    )
    return tmp_path


class TestEscape:
    def test_escapes_special_chars(self):
        assert "&amp;" in _escape("a & b")
        assert "&lt;" in _escape("<script>")
        assert "&gt;" in _escape(">")
        assert "&quot;" in _escape('"')
        assert "&#39;" in _escape("'")


class TestMarkdownToHtml:
    def test_headings(self):
        out = _render_markdown_to_html("# H1\n\n## H2\n\n### H3")
        assert "<h1>H1</h1>" in out
        assert "<h2>H2</h2>" in out
        assert "<h3>H3</h3>" in out

    def test_bold_and_italic(self):
        out = _render_markdown_to_html("**bold** and *italic*")
        assert "<strong>bold</strong>" in out
        assert "<em>italic</em>" in out

    def test_inline_code(self):
        out = _render_markdown_to_html("use `currentColor`")
        assert "<code>currentColor</code>" in out

    def test_fenced_code_block(self):
        out = _render_markdown_to_html("```python\nprint('hi')\n```")
        assert "<pre><code" in out
        assert 'language-python' in out
        assert "print(&#39;hi&#39;)" in out or "print('hi')" in out

    def test_link(self):
        out = _render_markdown_to_html("[Click here](./other.md)")
        assert '<a href="./other.md">Click here</a>' in out

    def test_table(self):
        out = _render_markdown_to_html("| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |")
        assert "<table>" in out
        assert "<th>A</th>" in out
        assert "<td>1</td>" in out

    def test_empty(self):
        assert _render_markdown_to_html("") == ""

    def test_escapes_html_in_body(self):
        out = _render_markdown_to_html("<script>alert('x')</script>")
        assert "&lt;script&gt;" in out  # not <script>


class TestGenerateHtml:
    def test_generates_html_file(self, sample_bundle):
        out = generate_html(sample_bundle)
        assert out.exists()
        assert out.name == "index.html"
        assert out.parent == sample_bundle

    def test_html_includes_concept_data(self, sample_bundle):
        out = generate_html(sample_bundle)
        content = out.read_text()

        # Contains both concepts' titles
        assert "Sales Invoice" in content
        assert "Frappe CSS Layout" in content

        # Contains both types in filter
        assert "Frappe DocType" in content
        assert "Claude Skill" in content

        # Contains both tags
        assert "billing" in content
        assert "css" in content

    def test_html_includes_concept_paths(self, sample_bundle):
        out = generate_html(sample_bundle)
        content = out.read_text()
        assert "doctypes/sales-invoice.md" in content
        assert "skills/frappe-css.md" in content

    def test_html_renders_body_as_html(self, sample_bundle):
        out = generate_html(sample_bundle)
        content = out.read_text()
        # Bold rendered
        assert "<strong>bold</strong>" in content
        # Code rendered
        assert "<code>currentColor</code>" in content

    def test_html_marks_missing_resource(self, sample_bundle):
        out = generate_html(sample_bundle)
        content = out.read_text()
        # The skills concept has no resource — should be marked
        assert "missing-resource" in content
        assert "(none" in content or "abstract concept" in content

    def test_html_self_contained(self, sample_bundle):
        """No external resources should be loaded."""
        out = generate_html(sample_bundle)
        content = out.read_text()
        # No CDN scripts (we use system fonts, no external CSS)
        assert "cdn." not in content.lower()
        assert "<script src=" not in content
        assert "<link rel=" not in content

    def test_html_under_500kb_for_small_bundle(self, sample_bundle):
        out = generate_html(sample_bundle)
        size_kb = out.stat().st_size / 1024
        assert size_kb < 50, f"Expected < 50 KB for 2 concepts, got {size_kb} KB"

    def test_html_meta_info(self, sample_bundle):
        out = generate_html(sample_bundle)
        content = out.read_text()
        # Bundle name appears in title + heading
        assert sample_bundle.name in content
        # OKF version mentioned
        assert "0.1" in content
        # Concept count
        assert "2 concepts" in content

    def test_custom_output_path(self, sample_bundle):
        out = generate_html(sample_bundle, output_path=sample_bundle / "viewer.html")
        assert out.name == "viewer.html"
        assert out.exists()

    def test_empty_bundle(self, tmp_path):
        """Bundle with no concepts still produces valid HTML."""
        out = generate_html(tmp_path)
        content = out.read_text()
        assert out.exists()
        assert "0 concepts" in content
        # Empty state shown when no concepts
        assert "No concepts" in content or "0 concepts" in content

    def test_dark_mode_support(self, sample_bundle):
        out = generate_html(sample_bundle)
        content = out.read_text()
        # Has dark mode media query
        assert "prefers-color-scheme: dark" in content
        assert "--bg:" in content  # CSS variable for background
        assert "var(--" in content  # Uses CSS variables

    def test_filter_dropdowns_populated(self, sample_bundle):
        """Type and tag filter dropdowns should include all values."""
        out = generate_html(sample_bundle)
        content = out.read_text()
        # Both types in typeFilter dropdown
        assert 'id="typeFilter"' in content
        assert ">Frappe DocType<" in content
        assert ">Claude Skill<" in content
        # All tags in tagFilter dropdown
        assert 'id="tagFilter"' in content
        assert ">billing<" in content
        assert ">erpnext<" in content
        assert ">css<" in content
