"""Skill Discovery & Analyzer Tool — Discovers and validates OpenCode skills.

Scans .opencode/skills/, ~/.config/opencode/skills/, .agents/skills/
Validates frontmatter (name, description, license, compatibility)
Reports skill availability and permission status per agent.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# Valid skill name pattern: lowercase alphanumeric with single hyphens
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_MAX_LENGTH = 64
SKILL_DESC_MAX_LENGTH = 1024

# Standard skill search paths
SKILL_PATHS = [
    # Project-local paths
    ".opencode/skills",
    ".claude/skills",
    ".agents/skills",
    # Global paths (relative to home)
]

GLOBAL_SKILL_PATHS = [
    "~/.config/opencode/skills",
    "~/.claude/skills",
    "~/.agents/skills",
]


@dataclass
class SkillInfo:
    """Parsed skill information."""

    name: str
    description: str
    path: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)
    is_valid: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    permission_status: dict[str, str] = field(default_factory=dict)  # agent -> allow/deny/ask


@dataclass
class SkillAnalysisResult:
    """Result of skill analysis."""

    skills: dict[str, SkillInfo] = field(default_factory=dict)
    search_paths: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skills": {
                name: {
                    "name": s.name,
                    "description": s.description,
                    "path": s.path,
                    "license": s.license,
                    "compatibility": s.compatibility,
                    "is_valid": s.is_valid,
                    "issues": s.issues,
                    "warnings": s.warnings,
                    "permission_status": s.permission_status,
                }
                for name, s in self.skills.items()
            },
            "search_paths": self.search_paths,
            "total_skills": len(self.skills),
            "valid_skills": sum(1 for s in self.skills.values() if s.is_valid),
            "issues": self.issues,
            "warnings": self.warnings,
        }


def discover_skills(project_root: Optional[Path] = None) -> list[tuple[Path, str]]:
    """Discover all skill files in standard locations.

    Returns:
        List of (path_to_SKILL.md, skill_name) tuples.
    """
    found = []
    root = project_root or Path.cwd()

    # Search project-local paths
    for rel_path in SKILL_PATHS:
        skills_dir = root / rel_path
        if skills_dir.exists() and skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file():
                    found.append((skill_file, skill_dir.name))

    # Search global paths
    for rel_path in GLOBAL_SKILL_PATHS:
        skills_dir = Path(os.path.expanduser(rel_path))
        if skills_dir.exists() and skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file():
                    found.append((skill_file, skill_dir.name))

    return found


def parse_frontmatter(file_path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a SKILL.md file."""
    content = file_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def validate_skill_name(name: str, dir_name: str) -> list[str]:
    """Validate a skill name against the rules."""
    issues = []

    if not name:
        issues.append("Skill name is empty")
        return issues

    if len(name) > SKILL_NAME_MAX_LENGTH:
        issues.append(f"Skill name exceeds {SKILL_NAME_MAX_LENGTH} characters ({len(name)})")

    if not SKILL_NAME_PATTERN.match(name):
        issues.append(
            f"Invalid skill name '{name}' — must be lowercase alphanumeric with single hyphens"
        )

    if name != dir_name:
        issues.append(
            f"Skill name '{name}' does not match directory name '{dir_name}'"
        )

    return issues


def validate_skill_description(description: str) -> list[str]:
    """Validate a skill description."""
    issues = []

    if not description:
        issues.append("Skill description is empty")
        return issues

    if len(description) > SKILL_DESC_MAX_LENGTH:
        issues.append(
            f"Description exceeds {SKILL_DESC_MAX_LENGTH} characters ({len(description)})"
        )

    return issues


def analyze_skills(
    project_root: Optional[Path] = None,
    config: Optional[dict[str, Any]] = None,
) -> SkillAnalysisResult:
    """Discover and analyze all skills.

    Args:
        project_root: Project root directory for local skill discovery.
        config: Optional OpenCode config for permission analysis.

    Returns:
        SkillAnalysisResult with discovered skills and validation results.
    """
    result = SkillAnalysisResult()

    # Discover skills
    skill_files = discover_skills(project_root)
    result.search_paths = [str(p) for p, _ in skill_files]

    # Track seen names for duplicate detection
    seen_names: dict[str, str] = {}  # name -> path

    for file_path, dir_name in skill_files:
        frontmatter = parse_frontmatter(file_path)
        name = frontmatter.get("name", dir_name)
        description = frontmatter.get("description", "")

        info = SkillInfo(
            name=name,
            description=description,
            path=str(file_path),
            license=frontmatter.get("license"),
            compatibility=frontmatter.get("compatibility"),
            metadata=frontmatter.get("metadata", {}) or {},
        )

        # Validate name
        name_issues = validate_skill_name(name, dir_name)
        info.issues.extend(name_issues)
        if name_issues:
            info.is_valid = False

        # Validate description
        desc_issues = validate_skill_description(description)
        info.issues.extend(desc_issues)
        if desc_issues:
            info.is_valid = False

        # Check for duplicates
        if name in seen_names:
            info.issues.append(
                f"Duplicate skill name '{name}' — already found at {seen_names[name]}"
            )
            info.is_valid = False
            result.issues.append(f"Duplicate skill name: {name}")
        else:
            seen_names[name] = str(file_path)

        # Check permissions if config provided
        if config:
            info.permission_status = _resolve_skill_permissions(name, config)

        result.skills[name] = info

    # Check for skills with deny permissions
    for name, skill in result.skills.items():
        for agent, status in skill.permission_status.items():
            if status == "deny":
                skill.warnings.append(f"Denied for agent '{agent}'")

    return result


def _resolve_skill_permissions(
    skill_name: str,
    config: dict[str, Any],
) -> dict[str, str]:
    """Resolve skill permission status for all agents."""
    permissions = {}

    # Check global skill permissions
    global_perms = config.get("permission", {})
    if isinstance(global_perms, dict):
        skill_rules = global_perms.get("skill", {})
        if isinstance(skill_rules, str):
            permissions["global"] = skill_rules
        elif isinstance(skill_rules, dict):
            import fnmatch
            for pattern, action in skill_rules.items():
                if fnmatch.fnmatch(skill_name, pattern):
                    permissions["global"] = action

    # Check agent-specific skill permissions
    agents = config.get("agent", {})
    for agent_name, agent_config in agents.items():
        if isinstance(agent_config, dict):
            agent_perms = agent_config.get("permission", {})
            if isinstance(agent_perms, dict):
                skill_rules = agent_perms.get("skill", {})
                if isinstance(skill_rules, str):
                    permissions[agent_name] = skill_rules
                elif isinstance(skill_rules, dict):
                    import fnmatch
                    for pattern, action in skill_rules.items():
                        if fnmatch.fnmatch(skill_name, pattern):
                            permissions[agent_name] = action

    return permissions
