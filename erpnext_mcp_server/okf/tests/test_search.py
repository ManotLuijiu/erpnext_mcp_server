"""Tests for search.py — pure Python, no Frappe dep."""

import pytest

from erpnext_mcp_server.okf.search import (
    list_concepts,
    get_concept,
    search_bundle,
    recommend_skill,
)
from erpnext_mcp_server.okf.writer import write_concept


@pytest.fixture
def sample_bundle(tmp_path):
    """Create a small bundle with 3 concepts for testing."""
    (tmp_path / "doctypes").mkdir()
    (tmp_path / "skills").mkdir()

    write_concept(
        tmp_path / "doctypes" / "sales-invoice.md",
        {
            "type": "Frappe DocType",
            "title": "Sales Invoice",
            "description": "Standard sales invoice",
            "tags": ["billing", "erpnext"],
        },
        "Sales Invoice is the standard billing document.\nIt has customer, items, grand_total.",
    )
    write_concept(
        tmp_path / "doctypes" / "thai-bank-statement-import.md",
        {
            "type": "Frappe DocType",
            "title": "Thai Bank Statement Import",
            "description": "KBank statement importer",
            "tags": ["banking", "kbank"],
        },
        "Imports KBank CSV files. Duplicate detection via fingerprint.",
    )
    write_concept(
        tmp_path / "skills" / "frappe-gmail-oauth.md",
        {
            "type": "Claude Skill",
            "title": "Frappe Gmail OAuth",
            "description": "OAuth setup for Gmail SMTP",
            "tags": ["gmail", "oauth"],
        },
        "Gmail OAuth Frappe v16 uses Connected App + Token Cache.",
    )
    return tmp_path


class TestListConcepts:
    def test_list_all(self, sample_bundle):
        concepts = list_concepts(sample_bundle)
        assert len(concepts) == 3

    def test_filter_by_type(self, sample_bundle):
        doctypes = list_concepts(sample_bundle, type="Frappe DocType")
        assert len(doctypes) == 2
        assert all(c["type"] == "Frappe DocType" for c in doctypes)

    def test_filter_by_tag(self, sample_bundle):
        banking = list_concepts(sample_bundle, tag="banking")
        assert len(banking) == 1
        assert "Thai Bank" in banking[0]["title"]


class TestGetConcept:
    def test_get_existing(self, sample_bundle):
        concept = get_concept(sample_bundle, "doctypes/sales-invoice.md")
        assert concept is not None
        assert concept["frontmatter"]["title"] == "Sales Invoice"
        assert "customer" in concept["body"]

    def test_get_unsafe_path_rejected(self, sample_bundle):
        assert get_concept(sample_bundle, "../etc/passwd") is None
        assert get_concept(sample_bundle, "/etc/passwd") is None

    def test_get_nonexistent(self, sample_bundle):
        assert get_concept(sample_bundle, "doctypes/does-not-exist.md") is None


class TestSearchBundle:
    def test_find_by_title(self, sample_bundle):
        results = search_bundle(sample_bundle, "Sales Invoice")
        assert len(results) >= 1
        assert results[0]["path"] == "doctypes/sales-invoice.md"

    def test_find_by_tag(self, sample_bundle):
        results = search_bundle(sample_bundle, "kbank")
        assert any("thai-bank" in r["path"] for r in results)

    def test_find_by_body(self, sample_bundle):
        results = search_bundle(sample_bundle, "fingerprint")
        assert any("thai-bank" in r["path"] for r in results)

    def test_filter_by_type(self, sample_bundle):
        results = search_bundle(sample_bundle, "frappe", type="Claude Skill")
        assert len(results) >= 1
        assert all(r["type"] == "Claude Skill" for r in results)

    def test_no_results(self, sample_bundle):
        assert search_bundle(sample_bundle, "nonexistent_xyz_query") == []

    def test_empty_query(self, sample_bundle):
        assert search_bundle(sample_bundle, "") == []

    def test_limit(self, sample_bundle):
        results = search_bundle(sample_bundle, "frappe", limit=1)
        assert len(results) <= 1

    def test_snippet_includes_match(self, sample_bundle):
        results = search_bundle(sample_bundle, "fingerprint")
        assert len(results) > 0
        assert "fingerprint" in results[0]["snippet"].lower()

    def test_limit_capped_at_100(self, sample_bundle):
        # Should not crash even if limit > 100
        results = search_bundle(sample_bundle, "frappe", limit=999)
        assert len(results) <= 100


class TestRecommendSkill:
    def test_only_returns_skills(self, sample_bundle):
        results = recommend_skill(sample_bundle, "Gmail OAuth Frappe")
        assert len(results) >= 1
        assert all(r["type"] == "Claude Skill" for r in results)
