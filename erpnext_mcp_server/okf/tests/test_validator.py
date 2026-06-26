"""Tests for validator.py — pure Python, no Frappe dep."""

import pytest

from erpnext_mcp_server.okf.validator import (
    is_safe_bundle_name,
    is_safe_concept_path,
    resolve_safe_path,
    validate_concept,
    validate_bundle,
    BUNDLE_NAME_RE,
)


class TestBundleName:
    @pytest.mark.parametrize("name", [
        "aws-solution",
        "bunchee_prod",
        "test123",
        "a",
    ])
    def test_valid(self, name):
        assert is_safe_bundle_name(name), f"should accept: {name}"

    @pytest.mark.parametrize("name", [
        "../etc/passwd",
        "aws.solution",
        "AWS Solution",
        "",
        "/abs/path",
        "-leading-dash",
    ])
    def test_invalid(self, name):
        assert not is_safe_bundle_name(name), f"should reject: {name}"


class TestConceptPathSafety:
    def test_blocks_traversal(self):
        assert not is_safe_concept_path("../etc/passwd")
        assert not is_safe_concept_path("doctypes/../../../etc/passwd")

    def test_blocks_absolute(self):
        assert not is_safe_concept_path("/etc/passwd")
        assert not is_safe_concept_path("/abs/path.md")

    def test_blocks_null_byte(self):
        assert not is_safe_concept_path("doctypes/\x00evil.md")

    def test_accepts_normal(self):
        assert is_safe_concept_path("doctypes/sales-invoice.md")
        assert is_safe_concept_path("skills/frappe-gmail-oauth.md")
        assert is_safe_concept_path("index.md")


class TestResolveSafePath:
    def test_resolves_safe(self, tmp_path):
        (tmp_path / "doctypes").mkdir()
        target = resolve_safe_path(tmp_path, "doctypes/x.md")
        assert target is not None
        assert target == (tmp_path / "doctypes" / "x.md").resolve()

    def test_blocks_traversal(self, tmp_path):
        target = resolve_safe_path(tmp_path, "../etc/passwd")
        assert target is None

    def test_blocks_absolute(self, tmp_path):
        target = resolve_safe_path(tmp_path, "/etc/passwd")
        assert target is None

    def test_blocks_symlink_outside(self, tmp_path):
        outside = tmp_path.parent / "outside.md"
        outside.write_text("evil")
        symlink_path = tmp_path / "doctypes" / "inside.md"
        symlink_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            symlink_path.symlink_to(outside)
            # resolve_safe_path follows symlinks; should reject because it points outside
            target = resolve_safe_path(tmp_path, "doctypes/inside.md")
            assert target is None
        finally:
            outside.unlink()


class TestValidateConcept:
    def test_minimal_concept_ok(self):
        from erpnext_mcp_server.okf.validator import validate_concept
        e, w = validate_concept(
            {"frontmatter": {"type": "Test", "title": "Hi", "description": "Test desc", "tags": ["test"]}},
            __import__("pathlib").Path("test.md"),
        )
        assert e == []
        assert w == []   # has type + title + description + tags

    def test_missing_type_errors(self):
        e, w = validate_concept(
            {"frontmatter": {"title": "No Type"}},
            __import__("pathlib").Path("test.md"),
        )
        assert any("type" in err for err in e)

    def test_missing_recommended_warns(self):
        e, w = validate_concept(
            {"frontmatter": {"type": "Test"}},
            __import__("pathlib").Path("test.md"),
        )
        assert e == []
        assert any("title" in warn for warn in w)

    def test_tags_must_be_list(self):
        e, w = validate_concept(
            {"frontmatter": {"type": "Test", "title": "Hi", "tags": "not-a-list"}},
            __import__("pathlib").Path("test.md"),
        )
        assert any("tags" in warn for warn in w)


class TestValidateBundle:
    def test_missing_bundle_root(self, tmp_path):
        result = validate_bundle(tmp_path / "nonexistent")
        assert result["valid"] is False
        assert any("does not exist" in e for e in result["errors"])

    def test_empty_bundle(self, tmp_path):
        result = validate_bundle(tmp_path)
        assert result["valid"] is True
        assert result["concepts"] == 0
        assert not result["index_present"]
        assert any("index.md" in w for w in result["warnings"])

    def test_valid_bundle(self, tmp_path):
        from erpnext_mcp_server.okf.writer import write_concept
        (tmp_path / "doctypes").mkdir()
        write_concept(
            tmp_path / "doctypes" / "sales-invoice.md",
            {"type": "Frappe DocType", "title": "Sales Invoice", "tags": ["billing"]},
            "# Sales Invoice\n\nBody.",
        )
        result = validate_bundle(tmp_path)
        assert result["valid"] is True
        assert result["concepts"] == 1

    def test_bundle_with_malformed_concept(self, tmp_path):
        (tmp_path / "doctypes").mkdir()
        # Write a file with no frontmatter 'type'
        bad = tmp_path / "doctypes" / "broken.md"
        bad.write_text("# Just a title, no frontmatter\n")
        result = validate_bundle(tmp_path)
        assert result["valid"] is False
        assert any("missing required" in e for e in result["errors"])
