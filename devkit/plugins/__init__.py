"""Plugin System — Interface for custom analyzers.

Supports Python plugins, external tool integration, plugin discovery
and registration, and configuration.

Plugin errors don't crash the system.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class PluginInfo:
    """Metadata about a loaded plugin."""

    name: str
    version: str
    description: str
    author: str = ""
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "path": self.path,
        }


@dataclass
class PluginResult:
    """Result from a plugin analyzer."""

    plugin_name: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "error": self.error,
        }


class AnalyzerPlugin(ABC):
    """Base class for custom analyzer plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""

    @property
    def description(self) -> str:
        """Plugin description."""
        return ""

    @property
    def author(self) -> str:
        """Plugin author."""
        return ""

    @abstractmethod
    def analyze(self, config: dict[str, Any], config_path: str) -> PluginResult:
        """Run analysis on the OpenCode config.

        Args:
            config: Parsed OpenCode configuration.
            config_path: Path to the config file.

        Returns:
            PluginResult with findings and recommendations.
        """


@dataclass
class PluginRegistry:
    """Registry for loaded plugins."""

    plugins: dict[str, AnalyzerPlugin] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def register(self, plugin: AnalyzerPlugin) -> None:
        """Register a plugin instance."""
        self.plugins[plugin.name] = plugin

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name."""
        if name in self.plugins:
            del self.plugins[name]
            return True
        return False

    def get(self, name: str) -> Optional[AnalyzerPlugin]:
        """Get a plugin by name."""
        return self.plugins.get(name)

    def list_plugins(self) -> list[PluginInfo]:
        """List all registered plugins."""
        return [
            PluginInfo(
                name=p.name,
                version=p.version,
                description=p.description,
                author=p.author,
            )
            for p in self.plugins.values()
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugins": [p.to_dict() for p in self.list_plugins()],
            "count": len(self.plugins),
            "errors": self.errors,
        }


def discover_plugins(
    plugin_dirs: Optional[list[str]] = None,
    config: Optional[dict[str, Any]] = None,
) -> PluginRegistry:
    """Discover and load plugins from directories and config.

    Args:
        plugin_dirs: List of directories to scan for plugins.
        config: OpenCode config with plugin configuration.

    Returns:
        PluginRegistry with loaded plugins.
    """
    registry = PluginRegistry()

    # Load from directories
    if plugin_dirs:
        for directory in plugin_dirs:
            _load_from_directory(directory, registry)

    # Load from config
    if config:
        _load_from_config(config, registry)

    return registry


def run_plugin_analysis(
    registry: PluginRegistry,
    config: dict[str, Any],
    config_path: str,
) -> list[PluginResult]:
    """Run all registered plugins against a config.

    Args:
        registry: PluginRegistry with loaded plugins.
        config: Parsed OpenCode configuration.
        config_path: Path to the config file.

    Returns:
        List of PluginResults from all plugins.
    """
    results = []

    for name, plugin in registry.plugins.items():
        try:
            result = plugin.analyze(config, config_path)
            results.append(result)
        except Exception as e:
            results.append(PluginResult(
                plugin_name=name,
                error=f"Plugin '{name}' failed: {str(e)}",
            ))

    return results


def merge_plugin_results(
    base_report: dict[str, Any],
    plugin_results: list[PluginResult],
) -> dict[str, Any]:
    """Merge plugin results into the base analysis report.

    Args:
        base_report: The base analysis report.
        plugin_results: Results from plugin analysis.

    Returns:
        Updated report with plugin findings integrated.
    """
    merged = dict(base_report)

    all_findings = merged.get("findings", [])
    all_recommendations = merged.get("recommendations", [])

    for result in plugin_results:
        if result.error:
            all_findings.append({
                "severity": "error",
                "category": f"plugin:{result.plugin_name}",
                "message": result.error,
            })
        else:
            all_findings.extend(result.findings)
            all_recommendations.extend(result.recommendations)

    merged["findings"] = all_findings
    merged["recommendations"] = all_recommendations
    merged["plugin_results"] = [r.to_dict() for r in plugin_results]

    return merged


def _load_from_directory(directory: str, registry: PluginRegistry) -> None:
    """Load plugins from a directory."""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        registry.errors.append(f"Plugin directory not found: {directory}")
        return

    for filepath in dir_path.glob("*.py"):
        if filepath.name.startswith("_"):
            continue
        try:
            _load_plugin_from_file(filepath, registry)
        except Exception as e:
            registry.errors.append(f"Failed to load plugin {filepath.name}: {str(e)}")


def _load_plugin_from_file(filepath: Path, registry: PluginRegistry) -> None:
    """Load a plugin from a Python file."""
    spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec from {filepath}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[filepath.stem] = module
    spec.loader.exec_module(module)

    # Find AnalyzerPlugin subclasses
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, AnalyzerPlugin)
            and attr is not AnalyzerPlugin
        ):
            plugin = attr()
            registry.register(plugin)


def _load_from_config(config: dict[str, Any], registry: PluginRegistry) -> None:
    """Load plugins specified in config."""
    # Check for plugin configuration
    plugin_config = config.get("plugins", {})
    if isinstance(plugin_config, dict):
        enabled = plugin_config.get("enabled", [])
        plugin_dirs = plugin_config.get("directories", [])

        for directory in plugin_dirs:
            _load_from_directory(directory, registry)

        # Filter to enabled plugins
        if enabled:
            enabled_names = set(enabled)
            for name in list(registry.plugins.keys()):
                if name not in enabled_names:
                    registry.unregister(name)
