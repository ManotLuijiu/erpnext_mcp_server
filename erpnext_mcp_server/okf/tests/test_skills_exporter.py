"""Tests for skills_exporter.py — pure Python (no Frappe)."""

import pytest

from erpnext_mcp_server.okf.skills_exporter import export_skill, export_skills


SAMPLE_SKILL = """---
name: frappe-gmail-oauth
title: Frappe Gmail OAuth
description: Set up Gmail OAuth for Frappe v16 SMTP via Connected App.
tags:
  - gmail
  - oauth
  - frappe
---

# Frappe Gmail OAuth

## When to Use

User asks about Gmail, OAuth, SMTP, or Email Account.

## Procedure

1. Create Google Cloud project
2. Enable Gmail API
3. Configure OAuth consent screen
4. ...
"""


@pytest.fixture
def sample_skills_dir(tmp_path):
    """Create a directory tree with 2 SKILL.md files."""
    skill1_dir = tmp_path / "skill-one"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(SAMPLE_SKILL)

    skill2_dir = tmp_path / "skill-two"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text("""---
name: thai-bank-notifications
title: Thai Bank Notifications
description: Install Thai bank email notifications.
---

# Thai Bank Notifications

Sets up notifications for KBank imports.
""")
    return tmp_path


class TestExportSkill:
    def test_writes_concept(self, tmp_path):
        src = tmp_path / "my-skill" / "SKILL.md"
        src.parent.mkdir()
        src.write_text(SAMPLE_SKILL)

        result = export_skill(src, tmp_path / "bundle")
        assert result["path"].endswith("skills/frappe-gmail-oauth.md")
        assert result["title"] == "Frappe Gmail OAuth"
        assert "claude-skill" in result["tags"]

    def test_concept_has_required_fields(self, tmp_path):
        src = tmp_path / "s" / "SKILL.md"
        src.parent.mkdir()
        src.write_text(SAMPLE_SKILL)
        export_skill(src, tmp_path / "bundle")

        from erpnext_mcp_server.okf.parser import parse_concept
        out = tmp_path / "bundle" / "skills" / "frappe-gmail-oauth.md"
        parsed = parse_concept(out.read_text())
        assert parsed["frontmatter"]["type"] == "Claude Skill"
        assert parsed["frontmatter"]["title"] == "Frappe Gmail OAuth"
        assert "Gmail" in parsed["body"]

    def test_refuses_non_skill_md(self, tmp_path):
        bad = tmp_path / "README.md"
        bad.write_text("Not a skill")
        with pytest.raises(ValueError, match="Not a SKILL.md"):
            export_skill(bad, tmp_path / "bundle")

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            export_skill(tmp_path / "missing" / "SKILL.md", tmp_path / "bundle")


class TestExportSkills:
    def test_exports_all_in_tree(self, sample_skills_dir, tmp_path):
        bundle = tmp_path / "bundle"
        results = export_skills(sample_skills_dir, bundle)
        assert len(results) == 2
        titles = {r["title"] for r in results}
        assert "Frappe Gmail OAuth" in titles
        assert "Thai Bank Notifications" in titles

    def test_skips_already_exported(self, sample_skills_dir, tmp_path):
        bundle = tmp_path / "bundle"
        first = export_skills(sample_skills_dir, bundle)         # first pass
        second = export_skills(sample_skills_dir, bundle)        # second pass — no overwrite
        # First pass exported all 2, second pass skipped all (no overwrite)
        assert len(first) == 2
        assert len(second) == 0

    def test_overwrite_re_exports(self, sample_skills_dir, tmp_path):
        bundle = tmp_path / "bundle"
        export_skills(sample_skills_dir, bundle)
        results = export_skills(sample_skills_dir, bundle, overwrite=True)
        assert len(results) == 2

    def test_nonexistent_root(self, tmp_path):
        assert export_skills(tmp_path / "nope", tmp_path / "bundle") == []
