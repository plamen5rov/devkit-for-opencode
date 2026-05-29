"""Tests for the Config Diff Tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devkit.tools.config_diff import (
    ConfigDiff,
    DiffEntry,
    diff_configs,
    diff_config_files,
    diff_config_strings,
    diff_config_against_history,
    _deep_diff,
    _find_section,
    _format_value,
    _group_by_section,
    _parse_jsonc,
)


def test_diff_identical_configs():
    config = {"model": "test/model", "permission": {"*": "ask"}}
    result = diff_configs(config, config)
    assert result.total_changes == 0
    assert result.added_count == 0
    assert result.removed_count == 0
    assert result.changed_count == 0


def test_diff_added_field():
    left = {"model": "a/model"}
    right = {"model": "a/model", "small_model": "b/model"}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.added_count == 1
    assert result.entries[0].change_type == "added"
    assert result.entries[0].path == "small_model"


def test_diff_removed_field():
    left = {"model": "a/model", "small_model": "b/model"}
    right = {"model": "a/model"}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.removed_count == 1
    assert result.entries[0].change_type == "removed"
    assert result.entries[0].path == "small_model"


def test_diff_changed_field():
    left = {"model": "a/old-model"}
    right = {"model": "b/new-model"}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.changed_count == 1
    assert result.entries[0].change_type == "changed"
    assert result.entries[0].path == "model"
    assert result.entries[0].left_value == "a/old-model"
    assert result.entries[0].right_value == "b/new-model"


def test_diff_nested_change():
    left = {"agent": {"main": {"model": "a/old"}}}
    right = {"agent": {"main": {"model": "b/new"}}}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].change_type == "changed"
    assert result.entries[0].path == "agent.main.model"


def test_diff_nested_added():
    left = {"agent": {"main": {"model": "a/model"}}}
    right = {"agent": {"main": {"model": "a/model", "temperature": 0.5}}}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].change_type == "added"
    assert result.entries[0].path == "agent.main.temperature"


def test_diff_nested_removed():
    left = {"agent": {"main": {"model": "a/model", "temperature": 0.5}}}
    right = {"agent": {"main": {"model": "a/model"}}}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].change_type == "removed"
    assert result.entries[0].path == "agent.main.temperature"


def test_diff_list_changed():
    left = {"plugin": ["pkg-a@1", "pkg-b@1"]}
    right = {"plugin": ["pkg-a@1", "pkg-c@2"]}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].change_type == "changed"
    assert result.entries[0].path == "plugin[1]"


def test_diff_list_added_item():
    left = {"plugin": ["pkg-a@1"]}
    right = {"plugin": ["pkg-a@1", "pkg-b@1"]}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].change_type == "added"
    assert result.entries[0].path == "plugin[1]"


def test_diff_list_removed_item():
    left = {"plugin": ["pkg-a@1", "pkg-b@1"]}
    right = {"plugin": ["pkg-a@1"]}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].change_type == "removed"
    assert result.entries[0].path == "plugin[1]"


def test_diff_multiple_changes():
    left = {"model": "a/old", "permission": {"*": "ask"}}
    right = {"model": "b/new", "permission": {"*": "allow"}, "share": "disabled"}
    result = diff_configs(left, right)
    assert result.total_changes == 3
    assert result.changed_count == 2
    assert result.added_count == 1
    paths = {e.path for e in result.entries}
    assert "model" in paths
    assert "permission.*" in paths
    assert "share" in paths


def test_diff_mixed_changes():
    left = {"model": "a/model", "old_field": "value"}
    right = {"model": "b/model", "new_field": "added"}
    result = diff_configs(left, right)
    assert result.total_changes == 3
    assert result.added_count == 1
    assert result.removed_count == 1
    assert result.changed_count == 1


def test_diff_empty_configs():
    result = diff_configs({}, {})
    assert result.total_changes == 0


def test_diff_from_empty():
    result = diff_configs({}, {"model": "a/model"})
    assert result.total_changes == 1
    assert result.entries[0].change_type == "added"


def test_diff_to_empty():
    result = diff_configs({"model": "a/model"}, {})
    assert result.total_changes == 1
    assert result.entries[0].change_type == "removed"


def test_diff_deep_nested():
    left = {"agent": {"main": {"permission": {"bash": "ask"}}}}
    right = {"agent": {"main": {"permission": {"bash": "allow"}}}}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].path == "agent.main.permission.bash"


def test_diff_mcp_server_list():
    left = {
        "mcp": {
            "servers": [
                {"name": "srv1", "command": "cmd1"}
            ]
        }
    }
    right = {
        "mcp": {
            "servers": [
                {"name": "srv1", "command": "cmd1"},
                {"name": "srv2", "command": "cmd2"}
            ]
        }
    }
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].change_type == "added"


def test_section_assigned():
    entry = DiffEntry(
        path="agent.main.model",
        left_value="old",
        right_value="new",
        change_type="changed",
        section="agent",
    )
    assert entry.section == "agent"


def test_section_unknown_field():
    entry = DiffEntry(
        path="custom.field.value",
        left_value=1,
        right_value=2,
        change_type="changed",
        section="other",
    )
    assert entry.section == "other"


def test_to_dict():
    result = diff_configs(
        {"model": "old"}, {"model": "new", "share": "disabled"},
        from_label="from", to_label="to",
    )
    d = result.to_dict()
    assert d["from_label"] == "from"
    assert d["to_label"] == "to"
    assert d["total_changes"] == 2
    assert len(d["entries"]) == 2
    assert d["entries"][0]["change_type"] in ("added", "changed")


def test_to_markdown():
    result = diff_configs(
        {"model": "old"}, {"model": "new"},
        from_label="from", to_label="to",
    )
    md = result.to_markdown()
    assert "# Config Diff Report" in md
    assert "**From:**" in md
    assert "**To:**" in md
    assert "model" in md
    assert "old" in md
    assert "new" in md


def test_to_markdown_no_changes():
    config = {"model": "a/model"}
    result = diff_configs(config, config)
    md = result.to_markdown()
    assert "No differences found" in md
    assert "identical" in md


def test_diff_config_files(tmp_path: Path):
    left_file = tmp_path / "left.json"
    right_file = tmp_path / "right.json"
    left_file.write_text(json.dumps({"model": "a/left"}))
    right_file.write_text(json.dumps({"model": "b/right"}))
    result = diff_config_files(str(left_file), str(right_file))
    assert result.total_changes == 1
    assert result.from_label == str(left_file)
    assert result.to_label == str(right_file)


def test_diff_config_files_missing():
    result = diff_config_files("/nonexistent/a.json", "/nonexistent/b.json")
    assert result.from_config == {}
    assert result.to_config == {}
    assert result.total_changes == 0


def test_diff_config_strings():
    result = diff_config_strings(
        '{"model": "a/old"}', '{"model": "b/new"}',
        from_label="v1", to_label="v2",
    )
    assert result.total_changes == 1
    assert result.from_label == "v1"
    assert result.to_label == "v2"


def test_diff_config_strings_invalid_json():
    result = diff_config_strings("not json", '{"model": "b"}')
    assert result.from_config == {}


def test_diff_config_strings_jsonc():
    result = diff_config_strings(
        '{"model": "a/model"} // comment',
        '{"model": "b/model"}',
    )
    assert result.total_changes == 1
    assert result.from_config == {"model": "a/model"}


def test_section_order_in_markdown():
    left = {"permission": {"*": "ask"}, "model": "a/model"}
    right = {"permission": {"*": "allow"}, "model": "b/model"}
    result = diff_configs(left, right)
    md = result.to_markdown()
    model_idx = md.index("model")
    permission_idx = md.index("permission")
    assert model_idx < permission_idx


def test_float_change():
    left = {"agent": {"main": {"temperature": 0.5}}}
    right = {"agent": {"main": {"temperature": 0.7}}}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].left_value == 0.5
    assert result.entries[0].right_value == 0.7


def test_bool_change():
    left = {"snapshot": True}
    right = {"snapshot": False}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].left_value is True
    assert result.entries[0].right_value is False


def test_null_value_change():
    left = {"model": None}
    right = {"model": "a/model"}
    result = diff_configs(left, right)
    assert result.total_changes == 1


def test_to_dict_entries_structure():
    result = diff_configs({"model": "a"}, {"model": "b"})
    d = result.to_dict()
    entry = d["entries"][0]
    assert "path" in entry
    assert "left_value" in entry
    assert "right_value" in entry
    assert "change_type" in entry
    assert "section" in entry


def test__deep_diff_direct():
    entries = []
    _deep_diff("root", "old_value", "new_value", entries)
    assert len(entries) == 1
    assert entries[0].change_type == "changed"


def test__deep_diff_same_values():
    entries = []
    _deep_diff("x", 42, 42, entries)
    assert len(entries) == 0


def test__find_section_known():
    assert _find_section("model") == "model"
    assert _find_section("agent.main.model") == "agent"
    assert _find_section("permission.*") == "permission"
    assert _find_section("mcp.servers[0].name") == "mcp"


def test__find_section_unknown():
    assert _find_section("unknown.field") == "other"
    assert _find_section("") == "root"


def test__format_value():
    assert _format_value(None) == "null"
    assert _format_value(True) == "true"
    assert _format_value(False) == "false"
    assert _format_value(42) == "42"
    assert _format_value("hello") == "hello"
    assert _format_value([1, 2, 3]) == "[1, 2, 3]"


def test__format_value_long():
    long_str = "x" * 100
    result = _format_value(long_str)
    assert len(result) <= 60
    assert result.endswith("...")


def test__group_by_section_ordering():
    entries = [
        DiffEntry(path="plugin[0]", left_value=None, right_value=None, change_type="added", section="plugin"),
        DiffEntry(path="model", left_value=None, right_value=None, change_type="changed", section="model"),
        DiffEntry(path="agent.tools", left_value=None, right_value=None, change_type="removed", section="agent"),
    ]
    grouped = _group_by_section(entries)
    keys = list(grouped.keys())
    assert keys[0] == "model"
    assert keys[1] == "agent"
    assert keys[2] == "plugin"


def test__parse_jsonc_comments():
    raw = """
    {
        "model": "a/model" // inline
    }
    """
    result = _parse_jsonc(raw)
    assert result == {"model": "a/model"}


def test__parse_jsonc_block_comments():
    raw = """
    /* header */
    {
        "model": "a/model"
    }
    """
    result = _parse_jsonc(raw)
    assert result == {"model": "a/model"}


def test__parse_jsonc_invalid():
    result = _parse_jsonc("not json")
    assert result == {}


def test_config_diff_from_config():
    left = {"model": "a/model", "share": "disabled"}
    right = {"model": "a/model", "share": "auto"}
    result = diff_configs(left, right)
    assert result.from_config == left
    assert result.to_config == right


def test_config_diff_default_labels():
    result = diff_configs({"a": 1}, {"a": 2})
    assert result.from_label == "from"
    assert result.to_label == "to"


def test_diff_permission_precedence():
    left = {"permission": {"*": "ask", "bash": "ask"}}
    right = {"permission": {"*": "ask", "bash": "allow"}}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.entries[0].path == "permission.bash"


def test_diff_agent_added():
    left = {}
    right = {"agent": {"coder": {"model": "a/model"}}}
    result = diff_configs(left, right)
    assert result.total_changes == 1
    assert result.added_count == 1


def test_to_markdown_empty_list():
    result = diff_configs({}, {})
    md = result.to_markdown()
    assert "No differences found" in md
    assert "Added | 0" in md
