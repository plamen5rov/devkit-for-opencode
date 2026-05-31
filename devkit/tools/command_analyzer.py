"""Command Analyzer Tool — Analyzes OpenCode custom slash commands.

Scans .opencode/commands/, ~/.config/opencode/commands/
Parses frontmatter (description, agent, model, subtask)
Validates placeholders ($ARGUMENTS, !`shell`, @file)
Reports command configuration and potential issues.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# Standard command search paths
COMMAND_PATHS = [
    ".opencode/commands",
]

GLOBAL_COMMAND_PATHS = [
    "~/.config/opencode/commands",
]

# Valid placeholders
PLACEHOLDER_PATTERN = re.compile(r"\$ARGUMENTS|\$\d+|!`[^`]+`|@[^\s]+")


@dataclass
class CommandInfo:
    """Parsed command information."""

    name: str
    description: str
    path: str
    template: str
    agent: Optional[str] = None
    model: Optional[str] = None
    subtask: bool = False
    placeholders: list[str] = field(default_factory=list)
    shell_commands: list[str] = field(default_factory=list)
    file_references: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CommandAnalysisResult:
    """Result of command analysis."""

    commands: dict[str, CommandInfo] = field(default_factory=dict)
    search_paths: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "commands": {
                name: {
                    "name": c.name,
                    "description": c.description,
                    "path": c.path,
                    "agent": c.agent,
                    "model": c.model,
                    "subtask": c.subtask,
                    "placeholders": c.placeholders,
                    "shell_commands": c.shell_commands,
                    "file_references": c.file_references,
                    "issues": c.issues,
                    "warnings": c.warnings,
                }
                for name, c in self.commands.items()
            },
            "search_paths": self.search_paths,
            "total_commands": len(self.commands),
            "issues": self.issues,
            "warnings": self.warnings,
        }


def discover_commands(project_root: Optional[Path] = None) -> list[tuple[Path, str]]:
    """Discover all command files in standard locations.

    Returns:
        List of (path_to_command.md, command_name) tuples.
    """
    found: list[tuple[Path, str]] = []

    # Search project-local paths (only if project_root is provided)
    if project_root is not None:
        for rel_path in COMMAND_PATHS:
            commands_dir = project_root / rel_path
            if commands_dir.exists() and commands_dir.is_dir():
                for cmd_file in commands_dir.glob("*.md"):
                    name = cmd_file.stem
                    found.append((cmd_file, name))

        # Search global paths (only alongside project-level scanning)
        for rel_path in GLOBAL_COMMAND_PATHS:
            commands_dir = Path(os.path.expanduser(rel_path))
            if commands_dir.exists() and commands_dir.is_dir():
                for cmd_file in commands_dir.glob("*.md"):
                    name = cmd_file.stem
                    found.append((cmd_file, name))

    return found


def parse_command_file(file_path: Path) -> tuple[dict[str, Any], str]:
    """Parse a command markdown file.

    Returns:
        Tuple of (frontmatter_dict, template_content).
    """
    content = file_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        return {}, content.strip()
    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        frontmatter = {}
    template = match.group(2).strip()
    return frontmatter, template


def extract_placeholders(template: str) -> list[str]:
    """Extract all placeholders from a command template."""
    return PLACEHOLDER_PATTERN.findall(template)


def extract_shell_commands(template: str) -> list[str]:
    """Extract shell command invocations from template."""
    pattern = re.compile(r"!`([^`]+)`")
    return pattern.findall(template)


def extract_file_references(template: str) -> list[str]:
    """Extract file references from template."""
    pattern = re.compile(r"@([^\s,;:!?\)]+)")
    refs = pattern.findall(template)
    # Strip trailing punctuation
    return [r.rstrip(".") for r in refs]


def analyze_commands(
    project_root: Optional[Path] = None,
    config: Optional[dict[str, Any]] = None,
) -> CommandAnalysisResult:
    """Discover and analyze all custom commands.

    Args:
        project_root: Project root directory for local command discovery.
        config: Optional OpenCode config for config-based command extraction.

    Returns:
        CommandAnalysisResult with discovered commands and validation results.
    """
    result = CommandAnalysisResult()

    # Discover commands
    command_files = discover_commands(project_root)
    result.search_paths = [str(p) for p, _ in command_files]

    # If no filesystem commands found and config is provided, extract from config
    if not command_files and config:
        commands_config = config.get("command", {})
        if isinstance(commands_config, dict):
            for name, cmd_config in commands_config.items():
                if isinstance(cmd_config, dict):
                    desc = cmd_config.get("description", "")
                else:
                    desc = ""
                info = CommandInfo(
                    name=name,
                    description=desc,
                    path="(from config)",
                    template="",
                    agent=cmd_config.get("agent") if isinstance(cmd_config, dict) else None,
                    model=cmd_config.get("model") if isinstance(cmd_config, dict) else None,
                    subtask=bool(cmd_config.get("subtask", False)) if isinstance(cmd_config, dict) else False,
                )
                if not info.description:
                    info.warnings.append("No description — commands should have a clear purpose")
                result.commands[name] = info
                result.warnings.extend(info.warnings)
        return result

    for file_path, name in command_files:
        frontmatter, template = parse_command_file(file_path)

        info = CommandInfo(
            name=name,
            description=frontmatter.get("description", ""),
            path=str(file_path),
            template=template,
            agent=frontmatter.get("agent"),
            model=frontmatter.get("model"),
            subtask=frontmatter.get("subtask", False),
        )

        # Extract placeholders
        info.placeholders = extract_placeholders(template)
        info.shell_commands = extract_shell_commands(template)
        info.file_references = extract_file_references(template)

        # Validate
        _validate_command(info)

        result.commands[name] = info
        result.issues.extend(info.issues)
        result.warnings.extend(info.warnings)

    return result


def _validate_command(info: CommandInfo) -> None:
    """Validate a command definition."""
    # Check for missing description
    if not info.description:
        info.warnings.append("No description — commands should have a clear purpose")

    # Check for missing template
    if not info.template:
        info.issues.append("Command has no template content")

    # Check for unused $ARGUMENTS placeholder
    if "$ARGUMENTS" in info.placeholders and not info.template.strip():
        info.warnings.append("$ARGUMENTS placeholder used but template is empty")

    # Check shell commands for dangerous patterns
    dangerous_patterns = ["rm -rf", "sudo", "curl | sh", "wget | bash"]
    for cmd in info.shell_commands:
        for pattern in dangerous_patterns:
            if pattern in cmd.lower():
                info.warnings.append(
                    f"Potentially dangerous shell command: '{cmd}'"
                )

    # Check file references for non-existent paths
    for ref in info.file_references:
        if ref.startswith("/") or ref.startswith("./"):
            # Could check if file exists, but skip for now (project-dependent)
            pass

    # Check model format
    if info.model and "/" not in info.model:
        info.warnings.append(
            f"Model '{info.model}' may be missing provider prefix (expected 'provider/model')"
        )

    # Check subagent with subtask
    if info.agent and info.subtask:
        info.warnings.append(
            f"Subtask enabled with agent '{info.agent}' — "
            "agent may be invoked twice"
        )
