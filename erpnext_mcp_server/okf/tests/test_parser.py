"""Tests for parser.py — pure Python, no Frappe dep."""

import pytest

from erpnext_mcp_server.okf.parser import (
    split_frontmatter,
    parse_frontmatter,
    parse_concept,
    parse_concept_safe,
    OKFParseError,
)


SAMPLE_CONCEPT = """---
type: Frappe DocType
title: Sales Invoice
description: Standard sales invoice document
tags:
  - billing
  - erpnext
timestamp: '2026-06-26T10:00:00Z'
---

# Sales Invoice

This is the body of the Sales Invoice concept.

## Fields

| Field | Type |
|---|---|
| customer | Link |
| grand_total | Currency |
"""


class TestSplitFrontmatter:
    def test_splits_well_formed(self):
        yaml_text, body = split_frontmatter(SAMPLE_CONCEPT)
        assert yaml_text is not None
        assert "type: Frappe DocType" in yaml_text
        assert body.startswith("\n# Sales Invoice")

    def test_no_frontmatter(self):
        text = "# Just a body\n\nNo frontmatter here."
        yaml_text, body = split_frontmatter(text)
        assert yaml_text is None
        assert body == text

    def test_empty_yaml(self):
        text = "---\n---\n\n# Body"
        yaml_text, body = split_frontmatter(text)
        assert yaml_text is not None
        assert body.lstrip().startswith("# Body")

    def test_unclosed_frontmatter_treated_as_body(self):
        text = "---\ntype: Test\n\n# Body with no closing"
        yaml_text, body = split_frontmatter(text)
        # No closing delimiter → whole text is body
        assert yaml_text is None


class TestParseFrontmatter:
    def test_parses_dict(self):
        fm = parse_frontmatter("type: Test\ntitle: Hello")
        assert fm == {"type": "Test", "title": "Hello"}

    def test_parses_list(self):
        fm = parse_frontmatter("tags:\n  - a\n  - b")
        assert fm == {"tags": ["a", "b"]}

    def test_empty_returns_empty_dict(self):
        assert parse_frontmatter(None) == {}
        assert parse_frontmatter("") == {}
        assert parse_frontmatter("   ") == {}

    def test_malformed_yaml_raises(self):
        with pytest.raises(OKFParseError):
            parse_frontmatter("type: :\n  - invalid")

    def test_non_dict_raises(self):
        with pytest.raises(OKFParseError):
            parse_frontmatter("- just\n- a list")


class TestParseConcept:
    def test_full_concept(self):
        result = parse_concept(SAMPLE_CONCEPT)
        assert result["frontmatter"]["type"] == "Frappe DocType"
        assert result["frontmatter"]["title"] == "Sales Invoice"
        assert "Sales Invoice" in result["body"]

    def test_body_only(self):
        result = parse_concept("# Just body\n\nNo frontmatter")
        assert result["frontmatter"] == {}
        assert "Just body" in result["body"]

    def test_round_trip_with_writer(self):
        from erpnext_mcp_server.okf.writer import assemble_concept
        fm = {"type": "Test", "title": "Round Trip", "tags": ["a", "b"]}
        body = "# Body\n\nSome content."
        text = assemble_concept(fm, body)
        parsed = parse_concept(text)
        assert parsed["frontmatter"]["type"] == "Test"
        assert "Some content." in parsed["body"]


class TestParseConceptSafe:
    def test_returns_none_on_error(self, tmp_path):
        # Create an unreadable / malformed file by passing non-existent path
        result = parse_concept_safe(tmp_path / "does-not-exist.md")
        assert result is None
