"""Tests for bundle.py — pure Python for generate_index and list_bundles."""

import pytest

from erpnext_mcp_server.okf.bundle import generate_index, list_bundles, OKF_VERSION
from erpnext_mcp_server.okf.writer import write_concept


class TestGenerateIndex:
    def test_generates_index_with_version(self, tmp_path):
        (tmp_path / "doctypes").mkdir()
        write_concept(
            tmp_path / "doctypes" / "a.md",
            {"type": "Test", "title": "Concept A"},
            "# A\n\nBody.",
        )
        idx_path = generate_index(tmp_path)
        assert idx_path.exists()
        content = idx_path.read_text()
        # YAML may quote the version; accept both forms
        assert (
            f"okf_version: {OKF_VERSION}" in content
            or f"okf_version: '{OKF_VERSION}'" in content
            or f'okf_version: "{OKF_VERSION}"' in content
        )
        assert "Concept A" in content
        assert "Test" in content

    def test_index_groups_by_subdir(self, tmp_path):
        (tmp_path / "doctypes").mkdir()
        (tmp_path / "skills").mkdir()
        write_concept(
            tmp_path / "doctypes" / "x.md",
            {"type": "Frappe DocType", "title": "Sales Invoice"},
            "# Sales Invoice",
        )
        write_concept(
            tmp_path / "skills" / "y.md",
            {"type": "Claude Skill", "title": "My Skill"},
            "# My Skill",
        )
        idx = generate_index(tmp_path)
        content = idx.read_text()
        assert "## doctypes" in content
        assert "## skills" in content

    def test_overwrites_existing_index(self, tmp_path):
        write_concept(
            tmp_path / "x.md",
            {"type": "Test", "title": "X"},
            "body",
        )
        # First generate
        generate_index(tmp_path)
        # Add another concept
        write_concept(
            tmp_path / "y.md",
            {"type": "Test", "title": "Y"},
            "body",
        )
        # Regenerate
        idx = generate_index(tmp_path)
        content = idx.read_text()
        # Index displays titles from frontmatter ("X" and "Y" here)
        assert "[X](x.md)" in content
        assert "[Y](y.md)" in content
        assert "Total concepts: 2" in content

    def test_handles_empty_bundle(self, tmp_path):
        idx = generate_index(tmp_path)
        assert idx.exists()
        content = idx.read_text()
        assert "No concepts yet" in content or "0 concepts" in content.lower()


class TestListBundles:
    def test_finds_marked_bundles(self, tmp_path):
        # Create a bundle by generating its index
        bundle = tmp_path / "my-bundle"
        bundle.mkdir()
        (bundle / "doctypes").mkdir()
        from erpnext_mcp_server.okf.writer import write_concept
        write_concept(
            bundle / "doctypes" / "a.md",
            {"type": "Test", "title": "A"},
            "body",
        )
        generate_index(bundle)

        bundles = list_bundles(tmp_path)
        assert len(bundles) == 1
        assert bundles[0]["name"] == "my-bundle"
        assert bundles[0]["okf_version"] == OKF_VERSION
        assert bundles[0]["concept_count"] == 1

    def test_ignores_unmarked_dirs(self, tmp_path):
        # A directory without okf_version index.md is not a bundle
        (tmp_path / "not-a-bundle").mkdir()
        (tmp_path / "not-a-bundle" / "random.md").write_text("# random")
        bundles = list_bundles(tmp_path)
        assert bundles == []

    def test_empty_root_returns_empty(self, tmp_path):
        assert list_bundles(tmp_path) == []
        assert list_bundles(tmp_path / "nonexistent") == []
