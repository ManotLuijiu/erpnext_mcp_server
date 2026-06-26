"""Claude Skills → OKF concept exporter.

Scans a directory tree for SKILL.md files (Claude Skills format) and exports
each as an OKF concept with `type: Claude Skill`.

Claude Skills format:
    my-skill/
    ├── SKILL.md           # YAML frontmatter + Markdown body
    ├── examples/
    └── scripts/

OKF frontmatter translation:
    type: Claude Skill
    title: <from frontmatter or directory name>
    description: <from frontmatter or first paragraph of body>
    tags: <from frontmatter + skill category if present>
    resource: file://<absolute path to SKILL.md>
    timestamp: <now>
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .writer import write_concept, OKFWriteError


def _parse_skill_frontmatter(skill_md_path: Path) -> tuple[dict[str, Any], str]:
    """Parse a Claude Skill SKILL.md into (frontmatter_dict, body).

    Uses the OKF parser since the format is identical (YAML + Markdown).
    """
    from .parser import parse_concept_safe
    parsed = parse_concept_safe(skill_md_path)
    if parsed is None:
        return {}, skill_md_path.read_text(encoding="utf-8")
    return parsed.get("frontmatter") or {}, parsed.get("body") or ""


def export_skill(
    skill_md_path: str | Path,
    bundle_root: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Export a single Claude Skill SKILL.md as an OKF concept.

    Returns:
        {"path": str, "title": str, "tags": list[str]}
    """
    src = Path(skill_md_path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"SKILL.md not found: {src}")
    if src.name != "SKILL.md":
        raise ValueError(f"Not a SKILL.md: {src}")

    skill_fm, skill_body = _parse_skill_frontmatter(src)
    skill_dir = src.parent

    # Claude Skills convention: name from frontmatter `name`, fallback to dir name
    name = skill_fm.get("name") or skill_dir.name
    title = skill_fm.get("title") or name.replace("-", " ").title()
    description = skill_fm.get("description") or ""
    tags = list(skill_fm.get("tags") or [])
    if not description and skill_body:
        # Use first non-empty paragraph
        for para in skill_body.split("\n\n"):
            para = para.strip()
            if para and not para.startswith("#"):
                description = para[:200]
                break

    # Build OKF concept body
    body_parts: list[str] = [
        f"# {title}",
        "",
        f"_Source_: `{src}`",
        f"_Skill directory_: `{skill_dir}`",
        "",
        "## When to Use",
        "",
    ]
    if description:
        body_parts.append(description)
        body_parts.append("")

    # Include the original skill body (verbatim, under a divider)
    if skill_body.strip():
        body_parts.append("## Original SKILL.md Body")
        body_parts.append("")
        body_parts.append(skill_body.strip())
        body_parts.append("")

    # Frontmatter translation table
    body_parts.append("## OKF Frontmatter Translation")
    body_parts.append("")
    body_parts.append("| Source | Value |")
    body_parts.append("|---|---|")
    body_parts.append(f"| Claude Skill `name` | `{name}` |")
    body_parts.append(f"| Claude Skill `title` | `{title}` |")
    body_parts.append(f"| Claude Skill `description` | `{description[:80]}{'...' if len(description) > 80 else ''}` |")
    body_parts.append(f"| Original SKILL.md | `{src}` |")
    body_parts.append("")

    body = "\n".join(body_parts)

    # Build OKF frontmatter
    okf_frontmatter = {
        "type": "Claude Skill",
        "title": title,
        "description": description or f"Claude Skill: {name}",
        "resource": f"file://{src}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tags": (tags + ["claude-skill", "skill"])[:8],
        "source_skill_md": str(src),
    }

    # Write under <bundle_root>/skills/<slug>.md
    out_path = Path(bundle_root) / "skills" / f"{name}.md"
    write_concept(out_path, okf_frontmatter, body, overwrite=overwrite)

    return {
        "path": str(out_path),
        "title": title,
        "tags": okf_frontmatter["tags"],
    }


def export_skills(
    skills_root: str | Path,
    bundle_root: str | Path,
    *,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    """Export all Claude Skills under skills_root as OKF concepts.

    Args:
        skills_root: Root directory to scan recursively for SKILL.md files
        bundle_root: OKF bundle root; concepts go under <bundle_root>/skills/
        overwrite: Overwrite existing concept files

    Returns:
        List of {"path", "title", "tags"} for each exported skill.
    """
    root = Path(skills_root)
    if not root.exists():
        return []

    exported: list[dict[str, Any]] = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        try:
            result = export_skill(skill_md, bundle_root, overwrite=overwrite)
            exported.append(result)
        except OKFWriteError as e:
            if "already exists" in str(e):
                # Already exported without overwrite — skip silently
                continue
            import logging
            logging.getLogger(__name__).warning(f"Skipped {skill_md}: {e}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Skipped {skill_md}: {e}")

    return exported
