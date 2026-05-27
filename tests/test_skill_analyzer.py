"""Tests for the Skill Discovery & Analyzer Tool."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from devkit.tools.skill_analyzer import (
    analyze_skills,
    parse_frontmatter,
    validate_skill_description,
    validate_skill_name,
)


@pytest.fixture
def valid_skill_dir(tmp_path: Path) -> Path:
    """Create a temporary valid skill directory."""
    skill_dir = tmp_path / ".opencode" / "skills" / "git-release"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: git-release
description: Create consistent releases and changelogs
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
---
## What I do
- Draft release notes from merged PRs
"""
    )
    return tmp_path


@pytest.fixture
def invalid_skill_dir(tmp_path: Path) -> Path:
    """Create a temporary invalid skill directory."""
    skill_dir = tmp_path / ".opencode" / "skills" / "Bad-Name"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: Bad-Name
description: ""
---
No description skill
"""
    )
    return tmp_path


@pytest.fixture
def duplicate_skill_dirs(tmp_path: Path) -> Path:
    """Create two directories with the same skill name."""
    # Project-local
    local_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    local_dir.mkdir(parents=True)
    (local_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Local version\n---\nContent"
    )

    # Global-like (simulated in same tmp)
    global_dir = tmp_path / ".agents" / "skills" / "my-skill"
    global_dir.mkdir(parents=True)
    (global_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Global version\n---\nContent"
    )

    return tmp_path


def test_valid_skill_discovery(valid_skill_dir: Path) -> None:
    """Test discovering a valid skill."""
    result = analyze_skills(valid_skill_dir)
    # Check that our skill was found (may also find global skills)
    assert "git-release" in result.skills
    skill = result.skills["git-release"]
    assert skill.name == "git-release"
    assert skill.license == "MIT"
    assert skill.compatibility == "opencode"
    assert skill.is_valid is True


def test_invalid_skill_name(invalid_skill_dir: Path) -> None:
    """Test detection of invalid skill name."""
    result = analyze_skills(invalid_skill_dir)
    assert "Bad-Name" in result.skills
    skill = result.skills["Bad-Name"]
    assert skill.is_valid is False
    assert any("Invalid skill name" in i for i in skill.issues)


def test_empty_description_warning(invalid_skill_dir: Path) -> None:
    """Test detection of empty description."""
    result = analyze_skills(invalid_skill_dir)
    skill = result.skills["Bad-Name"]
    assert any("empty" in i.lower() for i in skill.issues)


def test_duplicate_skill_detection(duplicate_skill_dirs: Path) -> None:
    """Test detection of duplicate skill names."""
    result = analyze_skills(duplicate_skill_dirs)
    assert any("Duplicate" in i for i in result.issues)


def test_parse_frontmatter(valid_skill_dir: Path) -> None:
    """Test parsing YAML frontmatter."""
    skill_file = valid_skill_dir / ".opencode" / "skills" / "git-release" / "SKILL.md"
    fm = parse_frontmatter(skill_file)
    assert fm["name"] == "git-release"
    assert fm["description"] == "Create consistent releases and changelogs"
    assert fm["license"] == "MIT"
    assert fm["metadata"]["audience"] == "maintainers"


def test_parse_no_frontmatter(tmp_path: Path) -> None:
    """Test parsing file without frontmatter."""
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# No frontmatter\nJust content")
    fm = parse_frontmatter(skill_file)
    assert fm == {}


def test_validate_skill_name_valid() -> None:
    """Test valid skill names."""
    assert validate_skill_name("git-release", "git-release") == []
    assert validate_skill_name("my-skill-123", "my-skill-123") == []
    assert validate_skill_name("a", "a") == []


def test_validate_skill_name_invalid() -> None:
    """Test invalid skill names."""
    issues = validate_skill_name("Bad-Name", "Bad-Name")
    assert len(issues) > 0

    issues = validate_skill_name("double--hyphen", "double--hyphen")
    assert len(issues) > 0

    issues = validate_skill_name("-starts-with-hyphen", "-starts-with-hyphen")
    assert len(issues) > 0


def test_validate_skill_name_mismatch() -> None:
    """Test name/directory mismatch."""
    issues = validate_skill_name("different-name", "actual-dir")
    assert any("does not match directory" in i for i in issues)


def test_validate_description_valid() -> None:
    """Test valid descriptions."""
    assert validate_skill_description("A valid description") == []


def test_validate_description_empty() -> None:
    """Test empty description."""
    issues = validate_skill_description("")
    assert any("empty" in i.lower() for i in issues)


def test_skill_permissions_deny() -> None:
    """Test skill permission resolution with deny."""
    config = {
        "permission": {
            "skill": {
                "*": "allow",
                "internal-*": "deny",
            },
        },
    }
    from devkit.tools.skill_analyzer import _resolve_skill_permissions
    perms = _resolve_skill_permissions("internal-tools", config)
    assert perms.get("global") == "deny"


def test_skill_permissions_allow() -> None:
    """Test skill permission resolution with allow."""
    config = {
        "permission": {
            "skill": "allow",
        },
    }
    from devkit.tools.skill_analyzer import _resolve_skill_permissions
    perms = _resolve_skill_permissions("any-skill", config)
    assert perms.get("global") == "allow"


def test_agent_skill_permissions() -> None:
    """Test agent-specific skill permissions."""
    config = {
        "agent": {
            "plan": {
                "permission": {
                    "skill": {
                        "*": "deny",
                        "documents-*": "allow",
                    },
                },
            },
        },
    }
    from devkit.tools.skill_analyzer import _resolve_skill_permissions
    perms = _resolve_skill_permissions("documents-writer", config)
    assert perms.get("plan") == "allow"


def test_to_dict_serialization(valid_skill_dir: Path) -> None:
    """Test result serialization to dict."""
    result = analyze_skills(valid_skill_dir)
    d = result.to_dict()
    assert "skills" in d
    assert "search_paths" in d
    assert "total_skills" in d
    assert "valid_skills" in d
    assert d["total_skills"] >= 1  # At least our test skill
    assert d["valid_skills"] >= 1
    assert "git-release" in d["skills"]
