"""Tests for the Command Analyzer Tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from devkit.tools.command_analyzer import (
    analyze_commands,
    extract_file_references,
    extract_placeholders,
    extract_shell_commands,
    parse_command_file,
)


@pytest.fixture
def valid_command_dir(tmp_path: Path) -> Path:
    """Create a temporary valid command directory."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "test.md"
    cmd_file.write_text(
        """---
description: Run tests with coverage
agent: build
model: anthropic/claude-sonnet-4-20250514
---
Run the full test suite with coverage report.
Focus on the failing tests and suggest fixes.
"""
    )
    return tmp_path


@pytest.fixture
def command_with_placeholders(tmp_path: Path) -> Path:
    """Create a command with various placeholders."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "create.md"
    cmd_file.write_text(
        """---
description: Create a new component
---
Create a new React component named $ARGUMENTS.
First argument: $1
Second argument: $2
Review the component in @src/components/Button.tsx.
"""
    )
    return tmp_path


@pytest.fixture
def command_with_shell(tmp_path: Path) -> Path:
    """Create a command with shell output injection."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "review.md"
    cmd_file.write_text(
        """---
description: Review recent changes
---
Recent git commits:
!`git log --oneline -10`
Review these changes and suggest improvements.
"""
    )
    return tmp_path


@pytest.fixture
def empty_command(tmp_path: Path) -> Path:
    """Create a command with no frontmatter."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "empty.md"
    cmd_file.write_text("")
    return tmp_path


def test_valid_command_discovery(valid_command_dir: Path) -> None:
    """Test discovering a valid command."""
    result = analyze_commands(valid_command_dir)
    assert "test" in result.commands
    cmd = result.commands["test"]
    assert cmd.description == "Run tests with coverage"
    assert cmd.agent == "build"
    assert cmd.model == "anthropic/claude-sonnet-4-20250514"


def test_command_with_placeholders(command_with_placeholders: Path) -> None:
    """Test command with various placeholders."""
    result = analyze_commands(command_with_placeholders)
    cmd = result.commands["create"]
    assert "$ARGUMENTS" in cmd.placeholders
    assert "$1" in cmd.placeholders
    assert "$2" in cmd.placeholders
    assert "src/components/Button.tsx" in cmd.file_references


def test_command_with_shell(command_with_shell: Path) -> None:
    """Test command with shell output injection."""
    result = analyze_commands(command_with_shell)
    cmd = result.commands["review"]
    assert len(cmd.shell_commands) == 1
    assert "git log --oneline -10" in cmd.shell_commands


def test_empty_command(empty_command: Path) -> None:
    """Test command with no content."""
    result = analyze_commands(empty_command)
    assert "empty" in result.commands
    cmd = result.commands["empty"]
    assert any("no template" in i.lower() for i in cmd.issues)


def test_parse_command_file(valid_command_dir: Path) -> None:
    """Test parsing a command file."""
    cmd_file = valid_command_dir / ".opencode" / "commands" / "test.md"
    fm, template = parse_command_file(cmd_file)
    assert fm["description"] == "Run tests with coverage"
    assert fm["agent"] == "build"
    assert "test suite" in template


def test_parse_no_frontmatter(tmp_path: Path) -> None:
    """Test parsing file without frontmatter."""
    cmd_file = tmp_path / "cmd.md"
    cmd_file.write_text("Just a template with no frontmatter")
    fm, template = parse_command_file(cmd_file)
    assert fm == {}
    assert template == "Just a template with no frontmatter"


def test_extract_placeholders() -> None:
    """Test placeholder extraction."""
    template = "Create $ARGUMENTS with $1 and $2"
    placeholders = extract_placeholders(template)
    assert "$ARGUMENTS" in placeholders
    assert "$1" in placeholders
    assert "$2" in placeholders


def test_extract_shell_commands() -> None:
    """Test shell command extraction."""
    template = "Result: !`npm test`\nCommits: !`git log --oneline -5`"
    cmds = extract_shell_commands(template)
    assert len(cmds) == 2
    assert "npm test" in cmds
    assert "git log --oneline -5" in cmds


def test_extract_file_references() -> None:
    """Test file reference extraction."""
    template = "Review @src/components/Button.tsx and @./styles/main.css"
    refs = extract_file_references(template)
    assert "src/components/Button.tsx" in refs
    assert "./styles/main.css" in refs


def test_dangerous_shell_warning(tmp_path: Path) -> None:
    """Test warning for dangerous shell commands."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "danger.md"
    cmd_file.write_text(
        """---
description: Dangerous command
---
Run this: !`rm -rf /tmp/*`
"""
    )
    result = analyze_commands(tmp_path)
    cmd = result.commands["danger"]
    assert any("dangerous" in w.lower() for w in cmd.warnings)


def test_missing_description_warning(tmp_path: Path) -> None:
    """Test warning for missing description."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "no-desc.md"
    cmd_file.write_text("---\n---\nTemplate content")
    result = analyze_commands(tmp_path)
    cmd = result.commands["no-desc"]
    assert any("No description" in w for w in cmd.warnings)


def test_bad_model_format_warning(tmp_path: Path) -> None:
    """Test warning for bad model format."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "bad-model.md"
    cmd_file.write_text(
        """---
description: Test command
model: claude-sonnet-4
---
Content
"""
    )
    result = analyze_commands(tmp_path)
    cmd = result.commands["bad-model"]
    assert any("provider prefix" in w for w in cmd.warnings)


def test_subtask_agent_warning(tmp_path: Path) -> None:
    """Test warning for subtask with agent."""
    cmd_dir = tmp_path / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True)
    cmd_file = cmd_dir / "double.md"
    cmd_file.write_text(
        """---
description: Double invocation
agent: build
subtask: true
---
Content
"""
    )
    result = analyze_commands(tmp_path)
    cmd = result.commands["double"]
    assert any("invoked twice" in w for w in cmd.warnings)


def test_empty_config() -> None:
    """Test analyzing with no local commands (global may still be found)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        result = analyze_commands(Path(tmp))
        # No local commands in tmp, but global may exist
        assert "test-cmd" not in result.commands  # Our tmp has no commands


def test_to_dict_serialization(valid_command_dir: Path) -> None:
    """Test result serialization to dict."""
    result = analyze_commands(valid_command_dir)
    d = result.to_dict()
    assert "commands" in d
    assert "search_paths" in d
    assert "total_commands" in d
    assert "test" in d["commands"]
    assert d["total_commands"] >= 1
