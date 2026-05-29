"""Tests for devkit.tools.graph_builder."""

from __future__ import annotations

from devkit.tools.graph_builder import (
    ConfigGraph,
    GraphEdge,
    GraphNode,
    build_config_graph,
    NODE_COLORS,
)


def test_empty_config():
    graph = build_config_graph({})
    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "config"


def test_models_extracted():
    config = {"model": "anthropic/claude-sonnet", "small_model": "anthropic/claude-haiku"}
    graph = build_config_graph(config)
    model_ids = {n.id for n in graph.nodes if n.type == "model"}
    assert "model:anthropic/claude-sonnet" in model_ids
    assert "model:anthropic/claude-haiku" in model_ids


def test_models_same_value_no_duplicate():
    config = {"model": "a/model", "small_model": "a/model"}
    graph = build_config_graph(config)
    model_nodes = [n for n in graph.nodes if n.type == "model"]
    assert len(model_nodes) == 1


def test_permissions_extracted():
    config = {"permission": {"*": "ask", "edit": "allow", "bash": "deny"}}
    graph = build_config_graph(config)
    perm_ids = {n.id for n in graph.nodes if n.type == "permission"}
    assert "perm:*" in perm_ids
    assert "perm:edit" in perm_ids
    assert "perm:bash" in perm_ids


def test_nested_permissions():
    config = {
        "permission": {
            "*": "ask",
            "bash": {"*": "ask", "git *": "allow", "npm *": "allow"},
        }
    }
    graph = build_config_graph(config)
    perm_ids = {n.id for n in graph.nodes if n.type == "permission"}
    assert "perm:bash.git *" in perm_ids
    assert "perm:bash.npm *" in perm_ids


def test_agents_extracted():
    config = {
        "agent": {
            "build": {"disabled": False, "model": "a/model"},
            "explore": {"disabled": True},
        }
    }
    graph = build_config_graph(config)
    agent_ids = {n.id for n in graph.nodes if n.type == "agent"}
    assert "agent:build" in agent_ids
    assert "agent:explore" in agent_ids

    agent_edges = [e for e in graph.edges if e.label == "defines agent"]
    assert len(agent_edges) == 2


def test_agent_model_edge():
    config = {"agent": {"build": {"model": "my-model"}}}
    graph = build_config_graph(config)
    model_edges = [e for e in graph.edges if e.label == "uses model"]
    assert len(model_edges) == 1
    assert model_edges[0].from_id == "agent:build"
    assert model_edges[0].to_id == "model:my-model"


def test_agent_peer_edges():
    config = {"agent": {"a": {}, "b": {}, "c": {}}}
    graph = build_config_graph(config)

    peer_edges = [e for e in graph.edges if e.label.startswith("peer")]
    assert len(peer_edges) == 3


def test_mcp_extracted():
    config = {
        "mcp": {
            "sentry": {"type": "remote", "url": "https://mcp.sentry.dev/mcp", "enabled": True},
            "local-tool": {"type": "local", "command": ["npx", "tool"], "enabled": False},
        }
    }
    graph = build_config_graph(config)
    mcp_ids = {n.id for n in graph.nodes if n.type == "mcp"}
    assert "mcp:sentry" in mcp_ids
    assert "mcp:local-tool" in mcp_ids

    mcp_edges = [e for e in graph.edges if e.label == "MCP server"]
    assert len(mcp_edges) == 2


def test_mcp_flat_structure():
    config = {
        "mcp": {
            "exa": {"type": "remote", "url": "https://mcp.exa.ai/mcp", "enabled": True},
        }
    }
    graph = build_config_graph(config)
    mcp_ids = {n.id for n in graph.nodes if n.type == "mcp"}
    assert "mcp:exa" in mcp_ids
    mcp_node = [n for n in graph.nodes if n.type == "mcp"][0]
    assert not mcp_node.extra.get("disabled", False)


def test_plugins_extracted():
    config = {"plugin": ["one@1.0", "two@2.0"]}
    graph = build_config_graph(config)
    plugin_ids = {n.id for n in graph.nodes if n.type == "plugin"}
    assert "plugin:one@1.0" in plugin_ids
    assert "plugin:two@2.0" in plugin_ids


def test_instructions_extracted():
    config = {"instructions": ["rules/COMMIT-REMINDER.md", "https://opencode.school/api/instructions"]}
    graph = build_config_graph(config)
    inst_ids = {n.id for n in graph.nodes if n.type == "instruction"}
    assert "instruction:rules/COMMIT-REMINDER.md" in inst_ids
    assert "instruction:https://opencode.school/api/instructions" in inst_ids

    url_node = [n for n in graph.nodes if "https" in n.id][0]
    assert url_node.extra["type"] == "url"
    file_node = [n for n in graph.nodes if n.id == "instruction:rules/COMMIT-REMINDER.md"][0]
    assert file_node.extra["type"] == "file"


def test_nodes_have_colors():
    config = {
        "model": "a/b",
        "permission": {"*": "ask"},
        "agent": {"x": {}},
        "mcp": {"s": {"type": "remote", "url": "http://e.com"}},
        "plugin": ["p@1"],
        "instructions": ["README.md"],
    }
    graph = build_config_graph(config)
    for node in graph.nodes:
        assert "color" in node.to_dict()
        assert node.to_dict()["color"] in NODE_COLORS.values()


def test_duplicate_prevention():
    config = {
        "model": "a/b",
        "small_model": "a/b",
        "agent": {"x": {"model": "a/b"}},
    }
    graph = build_config_graph(config)
    model_nodes = [n for n in graph.nodes if n.id == "model:a/b"]
    assert len(model_nodes) == 1


def test_to_dict_structure():
    config = {"model": "test/model"}
    graph = build_config_graph(config)
    d = graph.to_dict()
    assert "nodes" in d
    assert "edges" in d
    assert len(d["nodes"]) >= 2
    assert len(d["edges"]) >= 1

    node = d["nodes"][0]
    assert "id" in node
    assert "label" in node
    assert "type" in node
    assert "color" in node

    edge = d["edges"][0]
    assert "from" in edge
    assert "to" in edge
    assert "label" in edge


def test_config_label_custom():
    graph = build_config_graph({}, config_label="my-config.json")
    root = [n for n in graph.nodes if n.type == "config"][0]
    assert root.label == "my-config.json"


def test_permission_truncation():
    perms = {f"tool_{i}": "allow" for i in range(30)}
    config = {"permission": {**perms}}
    graph = build_config_graph(config)
    perm_nodes = [n for n in graph.nodes if n.type == "permission"]
    assert len(perm_nodes) <= 25


def test_graphnode_extra():
    node = GraphNode(id="x", label="X", type="test", extra={"key": "val"})
    d = node.to_dict()
    assert d["extra"]["key"] == "val"


def test_graphedge_type_fallback():
    edge = GraphEdge(from_id="a", to_id="b", label="custom")
    d = edge.to_dict()
    assert d["type"] == "custom"


def test_build_config_graph_full():
    config = {
        "model": "openai/gpt-4o",
        "small_model": "openai/gpt-4o-mini",
        "permission": {"*": "ask", "edit": "allow", "bash": {"*": "ask", "git *": "allow"}},
        "agent": {"build": {"model": "openai/gpt-4o", "disabled": False}, "plan": {"disabled": True}},
        "mcp": {"sentry": {"type": "remote", "url": "https://sentry.io/mcp", "enabled": True}},
        "plugin": ["pkg@1.0", "pkg@2.0"],
        "instructions": ["rules/COMMIT.md"],
    }
    graph = build_config_graph(config)
    assert len(graph.nodes) >= 10
    assert len(graph.edges) >= 8
