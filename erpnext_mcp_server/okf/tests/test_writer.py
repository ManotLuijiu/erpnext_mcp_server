"""Tests for writer.py — pure Python, no Frappe dep."""

import pytest

from erpnext_mcp_server.okf.writer import (
    assemble_concept,
    write_concept,
    slugify,
    concept_path_from_title,
    OKFWriteError,
)


class TestAssembleConcept:
    def test_with_frontmatter_and_body(self):
        text = assemble_concept(
            {"type": "Test", "title": "Hello"},
            "# Body\n\nContent.",
        )
        assert text.startswith("---\n")
        assert "---\n" in text[4:]
        assert "type: Test" in text
        assert "title: Hello" in text
        assert "# Body" in text

    def test_empty_frontmatter(self):
        text = assemble_concept({}, "# Body only")
        assert text.startswith("# Body only")

    def test_sorts_keys(self):
        text = assemble_concept(
            {"zebra": "z", "alpha": "a", "middle": "m"},
            "body",
        )
        # alpha should come before middle, middle before zebra
        alpha_pos = text.find("alpha")
        middle_pos = text.find("middle")
        zebra_pos = text.find("zebra")
        assert alpha_pos < middle_pos < zebra_pos


class TestSlugify:
    @pytest.mark.parametrize("input,expected", [
        ("Sales Invoice", "sales-invoice"),
        ("Thai Bank Statement Import", "thai-bank-statement-import"),
        ("Customer (Legacy)", "customer-legacy"),
        ("UPPERCASE", "uppercase"),
        ("  spaces  around  ", "spaces-around"),
        ("mixed_under_scores", "mixed-under-scores"),
        ("", "untitled"),
    ])
    def test_slugify(self, input, expected):
        assert slugify(input) == expected


class TestConceptPathFromTitle:
    def test_basic(self, tmp_path):
        path = concept_path_from_title(tmp_path, "doctypes", "Sales Invoice")
        assert path == tmp_path / "doctypes" / "sales-invoice.md"


class TestWriteConcept:
    def test_writes_file(self, tmp_path):
        out = write_concept(
            tmp_path / "test.md",
            {"type": "Test", "title": "Hello"},
            "# Body\n",
        )
        assert out.exists()
        content = out.read_text()
        assert "type: Test" in content
        assert "# Body" in content

    def test_creates_parent_dirs(self, tmp_path):
        out = write_concept(
            tmp_path / "deep" / "nested" / "test.md",
            {"type": "Test"},
            "body",
        )
        assert out.exists()

    def test_refuses_overwrite_by_default(self, tmp_path):
        write_concept(tmp_path / "test.md", {"type": "Test"}, "v1")
        with pytest.raises(OKFWriteError):
            write_concept(tmp_path / "test.md", {"type": "Test"}, "v2")

    def test_overwrite_true_replaces(self, tmp_path):
        write_concept(tmp_path / "test.md", {"type": "Test"}, "v1")
        write_concept(tmp_path / "test.md", {"type": "Test"}, "v2", overwrite=True)
        assert "v2" in (tmp_path / "test.md").read_text()

    def test_missing_type_raises(self, tmp_path):
        with pytest.raises(ValueError, match="must include"):
            write_concept(tmp_path / "test.md", {"title": "No Type"}, "body")

    def test_empty_type_raises(self, tmp_path):
        with pytest.raises(ValueError, match="must include"):
            write_concept(tmp_path / "test.md", {"type": ""}, "body")
