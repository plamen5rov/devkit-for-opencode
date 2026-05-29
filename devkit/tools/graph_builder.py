"""Graph Builder Tool — Extracts node/edge graph from OpenCode configs.

Builds a force-directed graph representation of an OpenCode configuration:
- Model nodes (main, small, agent-specific)
- Agent nodes with their properties
- MCP server nodes with connection status
- Plugin nodes for loaded packages
- Permission nodes for tool-level rules
- Instruction nodes for referenced files/URLs

Edges represent relationships: uses_model, has_permission, connects_to,
loads_plugin, includes, invokes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


NODE_COLORS: dict[str, str] = {
    "config": "#6366f1",
    "model": "#3b82f6",
    "agent": "#10b981",
    "mcp": "#f59e0b",
    "plugin": "#8b5cf6",
    "permission": "#ef4444",
    "instruction": "#06b6d4",
}


@dataclass
class GraphNode:
    id: str
    label: str
    type: str
    group: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "group": self.group or self.type,
            "color": NODE_COLORS.get(self.type, "#94a3b8"),
        }
        if self.extra:
            d["extra"] = self.extra
        return d


@dataclass
class GraphEdge:
    from_id: str
    to_id: str
    label: str
    type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "label": self.label,
            "type": self.type or self.label,
        }


@dataclass
class ConfigGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


def _ensure_node(graph: ConfigGraph, node_id: str, label: str, node_type: str, **extra: Any) -> None:
    for n in graph.nodes:
        if n.id == node_id:
            return
    graph.nodes.append(GraphNode(id=node_id, label=label, type=node_type, extra=extra))


def _add_edge(graph: ConfigGraph, from_id: str, to_id: str, label: str) -> None:
    for e in graph.edges:
        if e.from_id == from_id and e.to_id == to_id and e.label == label:
            return
    graph.edges.append(GraphEdge(from_id=from_id, to_id=to_id, label=label))


def build_config_graph(config: dict[str, Any], config_label: str = "opencode.json") -> ConfigGraph:
    """Build a force-directed graph from a parsed OpenCode configuration.

    Args:
        config: Parsed OpenCode config dict.
        config_label: Display label for the root config node.

    Returns:
        ConfigGraph with nodes and edges.
    """
    graph = ConfigGraph()

    _ensure_node(graph, "config", config_label, "config")

    _extract_models(graph, config)
    _extract_permissions(graph, config)
    _extract_agents(graph, config)
    _extract_mcp(graph, config)
    _extract_plugins(graph, config)
    _extract_instructions(graph, config)

    return graph


def _extract_models(graph: ConfigGraph, config: dict[str, Any]) -> None:
    main_model = config.get("model", "")
    small_model = config.get("small_model", "")

    if main_model:
        node_id = f"model:{main_model}"
        _ensure_node(graph, node_id, main_model, "model", role="primary")
        _add_edge(graph, "config", node_id, "primary model")

    if small_model and small_model != main_model:
        node_id = f"model:{small_model}"
        _ensure_node(graph, node_id, small_model, "model", role="small")
        _add_edge(graph, "config", node_id, "small model")


def _extract_permissions(graph: ConfigGraph, config: dict[str, Any]) -> None:
    permissions = config.get("permission", {})
    if not isinstance(permissions, dict):
        return

    wildcard = permissions.get("*", "")
    if wildcard:
        _ensure_node(graph, "perm:*", f"* ({wildcard})", "permission", rule=wildcard)
        _add_edge(graph, "config", "perm:*", "default permission")

    sorted_keys = sorted(k for k in permissions if k != "*")
    for key in sorted_keys[:20]:
        value = permissions[key]
        if isinstance(value, dict):
            for sub_key, sub_value in list(value.items())[:3]:
                node_id = f"perm:{key}.{sub_key}"
                label = f"{key} {sub_key} ({sub_value})"
                _ensure_node(graph, node_id, label, "permission", tool=key, rule=str(sub_value))
                _add_edge(graph, "config", node_id, "permission")
        elif isinstance(value, str):
            node_id = f"perm:{key}"
            _ensure_node(graph, node_id, f"{key} ({value})", "permission", tool=key, rule=value)
            _add_edge(graph, "config", node_id, "permission")


def _extract_agents(graph: ConfigGraph, config: dict[str, Any]) -> None:
    agents = config.get("agent", {})
    if not isinstance(agents, dict):
        return

    agent_names = list(agents.keys())
    other_agent_ids: list[str] = []

    for agent_name in agent_names:
        agent_cfg = agents[agent_name]
        if not isinstance(agent_cfg, dict):
            continue

        node_id = f"agent:{agent_name}"
        disabled = agent_cfg.get("disabled", False)
        agent_model = agent_cfg.get("model", "")

        label = f"{agent_name}"
        if disabled:
            label += " (disabled)"
        _ensure_node(graph, node_id, label, "agent", disabled=disabled)
        _add_edge(graph, "config", node_id, "defines agent")
        other_agent_ids.append(node_id)

        if agent_model:
            model_id = f"model:{agent_model}"
            _ensure_node(graph, model_id, agent_model, "model", role="agent")
            _add_edge(graph, node_id, model_id, "uses model")

    for from_i, from_id in enumerate(other_agent_ids):
        for to_j, to_id in enumerate(other_agent_ids):
            if from_i < to_j:
                from_name = from_id.replace("agent:", "")
                to_name = to_id.replace("agent:", "")
                _add_edge(graph, from_id, to_id, f"peer ({from_name} → {to_name})")


def _extract_mcp(graph: ConfigGraph, config: dict[str, Any]) -> None:
    mcp = config.get("mcp", {})
    if not isinstance(mcp, dict):
        return

    servers = mcp.get("servers", mcp)
    if not isinstance(servers, dict):
        return

    for server_name, server_cfg in list(servers.items()):
        if server_name in ("$schema", "type"):
            continue
        if not isinstance(server_cfg, dict):
            continue

        node_id = f"mcp:{server_name}"
        enabled = server_cfg.get("enabled", True)
        server_type = server_cfg.get("type", "unknown")
        server_url = server_cfg.get("url", "")

        label = f"{server_name} ({server_type})"
        if not enabled:
            label += " [off]"

        _ensure_node(graph, node_id, label, "mcp", type=server_type, url=server_url, enabled=enabled)
        _add_edge(graph, "config", node_id, "MCP server")


def _extract_plugins(graph: ConfigGraph, config: dict[str, Any]) -> None:
    plugins = config.get("plugin", [])
    if not isinstance(plugins, list):
        return

    for plugin in plugins[:10]:
        if not isinstance(plugin, str):
            continue
        node_id = f"plugin:{plugin}"
        _ensure_node(graph, node_id, plugin, "plugin")
        _add_edge(graph, "config", node_id, "loads plugin")


def _extract_instructions(graph: ConfigGraph, config: dict[str, Any]) -> None:
    instructions = config.get("instructions", [])
    if not isinstance(instructions, list):
        return

    for inst in instructions[:10]:
        if not isinstance(inst, str):
            continue
        inst_type = "url" if inst.startswith("http") else "file"
        short_label = inst.rsplit("/", 1)[-1] if "/" in inst else inst
        if len(short_label) > 40:
            short_label = short_label[:37] + "..."

        node_id = f"instruction:{inst}"
        _ensure_node(graph, node_id, short_label, "instruction", type=inst_type, path=inst)
        _add_edge(graph, "config", node_id, "includes")
