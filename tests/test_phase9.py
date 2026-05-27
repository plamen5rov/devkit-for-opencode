"""Tests for Phase 9: Multi-Agent Orchestration, Auto-Remediation, and Plugin System."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devkit.agents.config_auditor import AuditFinding, AuditResult, Severity
from devkit.agents.multi_agent import (
    MultiAgentReport,
    create_advisor_agent,
    create_auditor_agent,
    create_multi_agent_crew,
    create_orchestrator_agent,
    run_multi_agent_analysis,
)
from devkit.agents.optimization_advisor import OptimizationResult, Recommendation
from devkit.agents.orchestrator import OrchestratorResult
from devkit.plugins import (
    AnalyzerPlugin,
    PluginInfo,
    PluginRegistry,
    PluginResult,
    discover_plugins,
    merge_plugin_results,
    run_plugin_analysis,
)
from devkit.tasks.auto_fix import (
    Patch,
    RemediationResult,
    apply_patches_to_file,
    generate_patches,
)


@pytest.fixture
def valid_config(tmp_path: Path) -> Path:
    """Create a valid test config."""
    config = tmp_path / "opencode.json"
    config.write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "model": "anthropic/claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }))
    return config


@pytest.fixture
def bad_config(tmp_path: Path) -> Path:
    """Create a misconfigured test config."""
    config = tmp_path / "opencode.json"
    config.write_text(json.dumps({
        "model": "claude-sonnet-4-20250514",
        "tools": True,
        "share": True,
        "permission": {
            "bash": "allow",
            "edit": "allow",
        },
        "mcp": {
            "servers": {
                "disabled-server": {
                    "url": "https://example.com/mcp",
                    "enabled": False,
                },
                "secret-server": {
                    "url": "https://example.com/mcp",
                    "headers": {"api_key": "sk-live-secret"},
                },
            }
        },
        "agent": {
            "general": {
                "temperature": 1.5,
                "top_p": 2.0,
                "tools": ["read"],
            }
        },
    }))
    return config


# --- Multi-Agent Orchestration Tests ---

def test_multi_agent_report_to_dict():
    """Test MultiAgentReport serialization."""
    report = MultiAgentReport(
        config_path="/test.json",
        health_score=85,
        risk_score=90,
        aggregated_findings=[{"severity": "error", "message": "Test"}],
        aggregated_recommendations=[{"title": "Optimize", "description": "Save tokens"}],
    )
    d = report.to_dict()
    assert d["config_path"] == "/test.json"
    assert d["health_score"] == 85
    assert d["risk_score"] == 90
    assert len(d["aggregated_findings"]) == 1
    assert len(d["aggregated_recommendations"]) == 1


def test_multi_agent_report_to_markdown():
    """Test MultiAgentReport Markdown output."""
    report = MultiAgentReport(
        config_path="/test.json",
        health_score=85,
        risk_score=90,
        aggregated_findings=[{"severity": "error", "category": "sec", "message": "Test"}],
        aggregated_recommendations=[{"title": "Optimize", "description": "Save tokens"}],
    )
    md = report.to_markdown()
    assert "# Multi-Agent Analysis Report" in md
    assert "**Health Score:** 85/100" in md
    assert "**Risk Score:** 90/100" in md
    assert "Test" in md
    assert "Optimize" in md


def test_create_orchestrator_agent():
    """Test creating orchestrator agent."""
    agent = create_orchestrator_agent()
    assert agent.role == "Analysis Orchestrator"
    assert agent.allow_delegation is True


def test_create_auditor_agent():
    """Test creating auditor agent."""
    agent = create_auditor_agent()
    assert agent.role == "Config Auditor"
    assert agent.allow_delegation is False


def test_create_advisor_agent():
    """Test creating advisor agent."""
    agent = create_advisor_agent()
    assert agent.role == "Optimization Advisor"
    assert agent.allow_delegation is False


def test_create_multi_agent_crew():
    """Test creating multi-agent crew."""
    crew = create_multi_agent_crew("/test.json")
    assert len(crew.agents) == 3
    assert len(crew.tasks) == 3


def test_create_multi_agent_crew_hierarchical():
    """Test creating crew with hierarchical process."""
    crew = create_multi_agent_crew("/test.json", process="hierarchical")
    assert len(crew.agents) == 3


def test_aggregate_findings():
    """Test aggregating findings from multiple agents."""
    from devkit.agents.multi_agent import _aggregate_findings

    report = MultiAgentReport(config_path="/test.json")
    report.orchestrator_result = OrchestratorResult(
        config_path="/test.json",
        issues=["Issue 1"],
        warnings=["Warning 1"],
    )
    report.audit_result = AuditResult(
        config_path="/test.json",
        findings=[
            AuditFinding(severity=Severity.ERROR, category="sec", message="Error 1"),
            AuditFinding(severity=Severity.WARNING, category="perm", message="Warning 2"),
        ],
    )

    findings = _aggregate_findings(report)
    assert len(findings) == 4
    assert any(f["severity"] == "error" for f in findings)
    assert any(f["severity"] == "warning" for f in findings)


def test_aggregate_findings_deduplication():
    """Test that duplicate findings are deduplicated."""
    from devkit.agents.multi_agent import _aggregate_findings

    report = MultiAgentReport(config_path="/test.json")
    report.orchestrator_result = OrchestratorResult(
        config_path="/test.json",
        issues=["Same issue"],
    )
    report.audit_result = AuditResult(
        config_path="/test.json",
        findings=[
            AuditFinding(severity=Severity.ERROR, category="sec", message="Same issue"),
        ],
    )

    findings = _aggregate_findings(report)
    assert len(findings) == 1


def test_aggregate_recommendations():
    """Test aggregating recommendations."""
    from devkit.agents.multi_agent import _aggregate_recommendations

    report = MultiAgentReport(config_path="/test.json")
    report.optimization_result = OptimizationResult(
        config_path="/test.json",
        recommendations=[
            Recommendation(
                priority=1,
                category="mcp",
                title="Disable server",
                description="High cost",
                current_state="enabled",
                suggested_state="disabled",
                estimated_impact="Saves ~500 tokens/session",
                effort="low",
            ),
        ],
    )

    recs = _aggregate_recommendations(report)
    assert len(recs) == 1
    assert recs[0]["title"] == "Disable server"


def test_calculate_multi_agent_health():
    """Test health score calculation."""
    from devkit.agents.multi_agent import _calculate_multi_agent_health

    report = MultiAgentReport(config_path="/test.json")
    report.orchestrator_result = OrchestratorResult(
        config_path="/test.json",
        summary={"health_score": 80},
    )
    report.audit_result = AuditResult(
        config_path="/test.json",
        error_count=1,
        warning_count=2,
    )

    health = _calculate_multi_agent_health(report)
    assert health == 60  # 80 - 10 - 10


def test_calculate_multi_agent_risk():
    """Test risk score calculation."""
    from devkit.agents.multi_agent import _calculate_multi_agent_risk

    report = MultiAgentReport(config_path="/test.json")
    report.audit_result = AuditResult(
        config_path="/test.json",
        findings=[
            AuditFinding(severity=Severity.ERROR, category="sec", message="Error"),
            AuditFinding(severity=Severity.WARNING, category="perm", message="Warning"),
        ],
    )

    risk = _calculate_multi_agent_risk(report)
    assert risk == 77  # 100 - 15 - 8


@patch("devkit.agents.multi_agent.run_orchestration")
@patch("devkit.agents.multi_agent.run_audit")
@patch("devkit.agents.multi_agent.run_optimization")
def test_run_multi_agent_analysis(mock_opt, mock_audit, mock_orch, valid_config):
    """Test running multi-agent analysis."""
    mock_orch.return_value = OrchestratorResult(
        config_path=str(valid_config),
        summary={"health_score": 85},
    )
    mock_audit.return_value = AuditResult(
        config_path=str(valid_config),
        findings=[],
    )
    mock_opt.return_value = OptimizationResult(
        config_path=str(valid_config),
        recommendations=[],
    )

    report = run_multi_agent_analysis(str(valid_config))
    assert report.config_path == str(valid_config)
    assert report.orchestrator_result is not None
    assert report.audit_result is not None
    assert report.optimization_result is not None


# --- Auto-Remediation Tests ---

def test_generate_patches_permission_catch_all():
    """Test generating catch-all permission patch."""
    config = {"permission": {"bash": "allow"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        p.description == "Add catch-all permission rule"
        for p in result.patches
    )


def test_generate_patches_permission_bash():
    """Test generating bash tightening patch."""
    config = {"permission": {"*": "ask", "bash": "allow"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        p.description == "Remove globally allowed bash"
        for p in result.patches
    )


def test_generate_patches_permission_edit():
    """Test generating edit tightening patch."""
    config = {"permission": {"*": "ask", "edit": "allow"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        p.description == "Remove globally allowed edit"
        for p in result.patches
    )


def test_generate_patches_deprecated_tools():
    """Test generating deprecated tools field patch."""
    config = {"tools": True, "permission": {"*": "ask"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        p.description == "Remove deprecated 'tools' field"
        for p in result.patches
    )


def test_generate_patches_deprecated_share():
    """Test generating boolean share conversion patch."""
    config = {"share": True, "permission": {"*": "ask"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Convert boolean share to string" in p.description
        for p in result.patches
    )
    # Find the patch and check the after value
    share_patch = next(
        p for p in result.patches if "share" in p.description
    )
    assert share_patch.after == "manual"


def test_generate_patches_model_prefix():
    """Test generating model prefix patch."""
    config = {"model": "claude-sonnet-4-20250514", "permission": {"*": "ask"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Add provider prefix to model" in p.description
        for p in result.patches
    )
    model_patch = next(
        p for p in result.patches if "model" in p.description and "prefix" in p.description
    )
    assert model_patch.after == "anthropic/claude-sonnet-4-20250514"


def test_generate_patches_small_model():
    """Test generating small_model patch."""
    config = {"model": "anthropic/claude-sonnet-4-20250514", "permission": {"*": "ask"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Add small_model" in p.description
        for p in result.patches
    )


def test_generate_patches_disabled_mcp():
    """Test generating disabled MCP server removal patch."""
    config = {
        "permission": {"*": "ask"},
        "mcp": {
            "servers": {
                "disabled": {"url": "https://example.com", "enabled": False},
            }
        },
    }
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Remove disabled MCP server" in p.description
        for p in result.patches
    )


def test_generate_patches_mcp_secret():
    """Test generating MCP secret replacement patch."""
    config = {
        "permission": {"*": "ask"},
        "mcp": {
            "servers": {
                "sentry": {
                    "url": "https://example.com",
                    "headers": {"api_key": "sk-live-secret"},
                },
            }
        },
    }
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Replace hardcoded secret" in p.description
        for p in result.patches
    )


def test_generate_patches_agent_temperature():
    """Test generating agent temperature fix patch."""
    config = {
        "permission": {"*": "ask"},
        "agent": {
            "general": {"temperature": 1.5},
        },
    }
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Fix invalid temperature" in p.description
        for p in result.patches
    )
    temp_patch = next(
        p for p in result.patches if "temperature" in p.description
    )
    assert temp_patch.after == 0.7


def test_generate_patches_agent_top_p():
    """Test generating agent top_p fix patch."""
    config = {
        "permission": {"*": "ask"},
        "agent": {
            "general": {"top_p": 2.0},
        },
    }
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Fix invalid top_p" in p.description
        for p in result.patches
    )


def test_generate_patches_agent_tools():
    """Test generating agent tools removal patch."""
    config = {
        "permission": {"*": "ask"},
        "agent": {
            "general": {"tools": ["read"]},
        },
    }
    result = generate_patches(config, "/test.json", dry_run=True)

    assert any(
        "Remove deprecated 'tools' field from agent" in p.description
        for p in result.patches
    )


def test_generate_patches_category_filter():
    """Test filtering patches by category."""
    config = {
        "model": "claude-sonnet-4-20250514",
        "permission": {"*": "ask"},
    }
    result = generate_patches(config, "/test.json", categories=["model"])

    assert all(p.category == "model" for p in result.patches)


def test_generate_patches_dry_run():
    """Test dry run mode."""
    config = {"permission": {"*": "ask"}}
    result = generate_patches(config, "/test.json", dry_run=True)

    assert result.dry_run is True
    assert result.skipped_count == len(result.patches)
    assert result.applied_count == 0


def test_generate_patches_severity_ordering():
    """Test patches are sorted by severity."""
    config = {
        "model": "claude-sonnet-4-20250514",
        "permission": {"bash": "allow"},
    }
    result = generate_patches(config, "/test.json")

    severities = [p.severity for p in result.patches]
    severity_order = {"required": 0, "recommended": 1, "optional": 2}
    ordered = sorted(severities, key=lambda s: severity_order.get(s, 99))
    assert severities == ordered


def test_patch_to_dict():
    """Test Patch serialization."""
    patch = Patch(
        id="test-1",
        description="Test patch",
        category="test",
        severity="required",
        before="old",
        after="new",
        path="test.path",
    )
    d = patch.to_dict()
    assert d["id"] == "test-1"
    assert d["description"] == "Test patch"
    assert d["before"] == "old"
    assert d["after"] == "new"


def test_remediation_result_to_markdown():
    """Test RemediationResult Markdown output."""
    result = RemediationResult(
        config_path="/test.json",
        dry_run=True,
        patches=[
            Patch(
                id="test-1",
                description="Test patch",
                category="test",
                severity="required",
                before="old",
                after="new",
                path="test.path",
            ),
        ],
    )
    md = result.to_markdown()
    assert "# Auto-Remediation Report" in md
    assert "Test patch" in md
    assert "**Dry Run:** True" in md


def test_apply_patches_to_file(valid_config):
    """Test applying patches to a file."""
    result = apply_patches_to_file(str(valid_config), dry_run=False)

    assert result.dry_run is False
    assert result.migrated_config is not None


def test_apply_patches_to_file_output_path(valid_config, tmp_path):
    """Test applying patches with custom output path."""
    output = tmp_path / "patched.json"
    apply_patches_to_file(str(valid_config), output_path=str(output), dry_run=False)

    assert output.exists()
    patched = json.loads(output.read_text())
    assert patched is not None


def test_apply_patches_to_file_nonexistent():
    """Test applying patches to nonexistent file."""
    result = apply_patches_to_file("/nonexistent.json")
    assert result.patches == []


# --- Plugin System Tests ---

class TestPlugin(AnalyzerPlugin):
    """Test plugin for testing."""

    @property
    def name(self) -> str:
        return "test-plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A test plugin"

    @property
    def author(self) -> str:
        return "Test Author"

    def analyze(self, config: dict[str, Any], config_path: str) -> PluginResult:
        findings = []
        if "model" not in config:
            findings.append({
                "severity": "warning",
                "category": "model",
                "message": "No model configured",
            })
        return PluginResult(
            plugin_name=self.name,
            findings=findings,
            recommendations=[{"title": "Add model", "description": "Configure a model"}],
        )


class FailingPlugin(AnalyzerPlugin):
    """Plugin that always fails."""

    @property
    def name(self) -> str:
        return "failing-plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def analyze(self, config: dict[str, Any], config_path: str) -> PluginResult:
        raise RuntimeError("Plugin failure")


def test_plugin_registry_register():
    """Test registering a plugin."""
    registry = PluginRegistry()
    registry.register(TestPlugin())
    assert len(registry.plugins) == 1
    assert "test-plugin" in registry.plugins


def test_plugin_registry_unregister():
    """Test unregistering a plugin."""
    registry = PluginRegistry()
    registry.register(TestPlugin())
    assert registry.unregister("test-plugin") is True
    assert len(registry.plugins) == 0
    assert registry.unregister("nonexistent") is False


def test_plugin_registry_get():
    """Test getting a plugin."""
    registry = PluginRegistry()
    registry.register(TestPlugin())
    plugin = registry.get("test-plugin")
    assert plugin is not None
    assert plugin.name == "test-plugin"
    assert registry.get("nonexistent") is None


def test_plugin_registry_list():
    """Test listing plugins."""
    registry = PluginRegistry()
    registry.register(TestPlugin())
    plugins = registry.list_plugins()
    assert len(plugins) == 1
    assert plugins[0].name == "test-plugin"
    assert plugins[0].version == "1.0.0"


def test_plugin_registry_to_dict():
    """Test registry serialization."""
    registry = PluginRegistry()
    registry.register(TestPlugin())
    registry.errors.append("Test error")
    d = registry.to_dict()
    assert d["count"] == 1
    assert len(d["plugins"]) == 1
    assert d["errors"] == ["Test error"]


def test_plugin_info_to_dict():
    """Test PluginInfo serialization."""
    info = PluginInfo(
        name="test",
        version="1.0.0",
        description="Test",
        author="Author",
        path="/path",
    )
    d = info.to_dict()
    assert d["name"] == "test"
    assert d["version"] == "1.0.0"


def test_run_plugin_analysis():
    """Test running plugin analysis."""
    registry = PluginRegistry()
    registry.register(TestPlugin())
    registry.register(FailingPlugin())

    config = {"permission": {"*": "ask"}}
    results = run_plugin_analysis(registry, config, "/test.json")

    assert len(results) == 2
    # TestPlugin should succeed
    test_result = next(r for r in results if r.plugin_name == "test-plugin")
    assert test_result.error is None
    assert len(test_result.findings) == 1
    # FailingPlugin should report error
    fail_result = next(r for r in results if r.plugin_name == "failing-plugin")
    assert fail_result.error is not None
    assert "Plugin failure" in fail_result.error


def test_merge_plugin_results():
    """Test merging plugin results into base report."""
    base = {
        "findings": [{"severity": "error", "message": "Base finding"}],
        "recommendations": [{"title": "Base rec"}],
    }
    plugin_results = [
        PluginResult(
            plugin_name="test",
            findings=[{"severity": "warning", "message": "Plugin finding"}],
            recommendations=[{"title": "Plugin rec"}],
        ),
        PluginResult(
            plugin_name="failing",
            error="Plugin failed",
        ),
    ]

    merged = merge_plugin_results(base, plugin_results)
    assert len(merged["findings"]) == 3
    assert len(merged["recommendations"]) == 2
    assert len(merged["plugin_results"]) == 2


def test_discover_plugins_empty():
    """Test discovering plugins with no directories."""
    registry = discover_plugins()
    assert len(registry.plugins) == 0


def test_discover_plugins_nonexistent_directory():
    """Test discovering plugins from nonexistent directory."""
    registry = discover_plugins(["/nonexistent/plugins"])
    assert len(registry.errors) == 1


def test_discover_plugins_from_config():
    """Test discovering plugins from config."""
    config = {
        "plugins": {
            "enabled": ["test"],
            "directories": ["/nonexistent"],
        }
    }
    registry = discover_plugins(config=config)
    assert len(registry.errors) == 1
