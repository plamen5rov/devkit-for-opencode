"""CLI entry point for DevKit for OpenCode.

Usage:
    devkit analyze --config-path PATH [--format json|markdown|table]
    devkit audit --config-path PATH [--format json|markdown] [--fix]
    devkit score --config-path PATH [--format json|table] [--detailed]
    devkit history [--config-path PATH] [--limit N]
    devkit migrate --config-path PATH [--format json|markdown] [--diff]
    devkit diff --from PATH --to PATH [--format json|markdown]
    devkit --help
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from devkit import __version__
from devkit.memory.history import AnalysisHistoryStore
from devkit.memory.recommendations import RecommendationTracker


DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "devkit" / "history.db"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="devkit",
        description="DevKit for OpenCode — Analyze and optimize OpenCode configurations",
    )
    parser.add_argument("--version", action="version", version=f"devkit {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run full analysis pipeline")
    analyze_parser.add_argument("--config-path", type=str, default=None, help="Path to opencode.json")
    analyze_parser.add_argument("--format", dest="output_format", choices=["json", "markdown", "table"], default="json")
    analyze_parser.add_argument("--verbose", action="store_true")

    # audit
    audit_parser = subparsers.add_parser("audit", help="Run security audit")
    audit_parser.add_argument("--config-path", type=str, default=None, help="Path to opencode.json")
    audit_parser.add_argument("--format", dest="output_format", choices=["json", "markdown"], default="json")
    audit_parser.add_argument("--fix", action="store_true", help="Generate fixed config")
    audit_parser.add_argument("--verbose", action="store_true")

    # score
    score_parser = subparsers.add_parser("score", help="Calculate health score")
    score_parser.add_argument("--config-path", type=str, default=None, help="Path to opencode.json")
    score_parser.add_argument("--format", dest="output_format", choices=["json", "table"], default="json")
    score_parser.add_argument("--detailed", action="store_true", help="Show factor breakdown")
    score_parser.add_argument("--verbose", action="store_true")

    # history
    history_parser = subparsers.add_parser("history", help="View analysis history")
    history_parser.add_argument("--config-path", type=str, default=None, help="Filter by config path")
    history_parser.add_argument("--limit", type=int, default=10, help="Max records to show")
    history_parser.add_argument("--format", dest="output_format", choices=["json", "table"], default="table")
    history_parser.add_argument("--db-path", type=str, default=str(DEFAULT_DB_PATH), help="Path to history database")

    # migrate
    migrate_parser = subparsers.add_parser("migrate", help="Migration assistant")
    migrate_parser.add_argument("--config-path", type=str, default=None, help="Path to opencode.json")
    migrate_parser.add_argument("--format", dest="output_format", choices=["json", "markdown"], default="markdown")
    migrate_parser.add_argument("--diff", action="store_true", help="Show config diff")
    migrate_parser.add_argument("--verbose", action="store_true")

    # diff
    diff_parser = subparsers.add_parser("diff", help="Compare two configs")
    diff_parser.add_argument("--from", dest="from_path", type=str, default=None, help="Path to source config")
    diff_parser.add_argument("--to", dest="to_path", type=str, default=None, help="Path to target config")
    diff_parser.add_argument("--format", dest="output_format", choices=["json", "markdown"], default="markdown")
    diff_parser.add_argument("--verbose", action="store_true")

    graph_parser = subparsers.add_parser("graph", help="Build dependency graph from config")
    graph_parser.add_argument("--config-path", type=str, default=None, help="Path to opencode.json")
    graph_parser.add_argument("--output", dest="output_file", type=str, default=None, help="Write graph JSON to file")
    graph_parser.add_argument("--verbose", action="store_true")

    return parser.parse_args(argv)


def detect_config() -> Optional[Path]:
    """Auto-detect OpenCode config file."""
    import os

    candidates = [
        Path(".opencode/opencode.json"),
        Path(".opencode/opencode.jsonc"),
        Path(os.path.expanduser("~/.config/opencode/opencode.json")),
        Path(os.path.expanduser("~/.config/opencode/opencode.jsonc")),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as a simple table."""
    if not rows:
        return "No data"

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    data_lines = [" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) for row in rows]

    return "\n".join([header_line, separator] + data_lines)


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run full analysis pipeline."""
    from devkit.tasks.full_audit import create_full_audit_task

    config_path = Path(args.config_path) if args.config_path else detect_config()
    if not config_path or not config_path.exists():
        print("No OpenCode config found. Specify --config-path or place opencode.json in .opencode/")
        return 1

    report = create_full_audit_task(str(config_path))

    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, default=str))
    elif args.output_format == "markdown":
        print(report.to_markdown())
    else:  # table
        summary = report.summary
        print(f"Health Score: {summary.get('health_score', 0)}/100")
        table_data = format_table(
            ["Metric", "Value"],
            [
                ["Issues", str(summary.get("total_issues", 0))],
                ["Warnings", str(summary.get("total_warnings", 0))],
                ["Agents", str(summary.get("agent_count", 0))],
                ["Skills", str(summary.get("skill_count", 0))],
                ["MCP Servers", str(summary.get("mcp_count", 0))],
                ["Commands", str(summary.get("command_count", 0))],
            ],
        )
        print(f"\n{table_data}")

    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Run security audit."""
    from devkit.tasks.security_scan import run_security_scan

    config_path = Path(args.config_path) if args.config_path else detect_config()
    if not config_path or not config_path.exists():
        print("No OpenCode config found. Specify --config-path or place opencode.json in .opencode/")
        return 1

    result = run_security_scan(str(config_path))

    if args.output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:  # markdown
        print(result.to_markdown())

    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """Calculate health score."""
    from devkit.agents.orchestrator import run_orchestration

    config_path = Path(args.config_path) if args.config_path else detect_config()
    if not config_path or not config_path.exists():
        print("No OpenCode config found. Specify --config-path or place opencode.json in .opencode/")
        return 1

    result = run_orchestration(str(config_path))
    score = result.summary.get("health_score", 0)

    if args.output_format == "json":
        output = {"health_score": score, "summary": result.summary}
        if args.detailed:
            output["breakdown"] = {
                "issues": result.summary.get("total_issues", 0),
                "warnings": result.summary.get("total_warnings", 0),
                "agents": result.summary.get("agent_count", 0),
                "skills": result.summary.get("skill_count", 0),
                "mcp_servers": result.summary.get("mcp_count", 0),
                "commands": result.summary.get("command_count", 0),
                "mcp_token_estimate": result.summary.get("mcp_token_estimate", 0),
            }
        print(json.dumps(output, indent=2))
    else:  # table
        print(f"Health Score: {score}/100")
        if args.detailed:
            table_data = format_table(
                ["Factor", "Value"],
                [
                    ["Issues", str(result.summary.get("total_issues", 0))],
                    ["Warnings", str(result.summary.get("total_warnings", 0))],
                    ["Agents", str(result.summary.get("agent_count", 0))],
                    ["Skills", str(result.summary.get("skill_count", 0))],
                    ["MCP Servers", str(result.summary.get("mcp_count", 0))],
                    ["Commands", str(result.summary.get("command_count", 0))],
                    ["MCP Token Estimate", f"~{result.summary.get('mcp_token_estimate', 0)} tokens"],
                ],
            )
            print(f"\n{table_data}")

    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """View analysis history."""
    db_path = Path(args.db_path)
    if not db_path.exists():
        print("No analysis history found.")
        return 0

    store = AnalysisHistoryStore(db_path)

    if args.config_path:
        records = store.query_by_config_path(args.config_path)
    else:
        records = store.get_latest()
        records = [records] if records else []

    records = records[: args.limit]

    if not records:
        print("No analysis records found.")
        return 0

    if args.output_format == "json":
        data = [r.to_dict() for r in records]
        print(json.dumps(data, indent=2, default=str))
    else:  # table
        headers = ["#", "Config Path", "Health", "Risk", "Issues", "Warnings", "Date"]
        rows = [
            [
                str(i + 1),
                r.config_path,
                str(r.health_score),
                str(r.risk_score),
                str(r.issue_count),
                str(r.warning_count),
                r.timestamp[:19],
            ]
            for i, r in enumerate(records)
        ]
        print(format_table(headers, rows))

    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Migration assistant."""
    from devkit.tasks.migration_assistant import run_migration_analysis

    config_path = Path(args.config_path) if args.config_path else detect_config()
    if not config_path or not config_path.exists():
        print("No OpenCode config found. Specify --config-path or place opencode.json in .opencode/")
        return 1

    result = run_migration_analysis(str(config_path))

    if args.output_format == "json":
        output = result.to_dict()
        if args.diff:
            output["diff"] = result.migrated_config
        print(json.dumps(output, indent=2, default=str))
    else:  # markdown
        print(result.to_markdown())
        if args.diff and result.migrated_config:
            print("\n## Migrated Config\n")
            print("```json")
            print(json.dumps(result.migrated_config, indent=2))
            print("```")

    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare two configs."""
    from devkit.tools.config_diff import diff_config_files

    from_path = Path(args.from_path) if args.from_path else None
    to_path = Path(args.to_path) if args.to_path else None

    if not from_path or not from_path.exists():
        print("No source config found. Specify --from PATH.")
        return 1
    if not to_path or not to_path.exists():
        print("No target config found. Specify --to PATH.")
        return 1

    result = diff_config_files(str(from_path), str(to_path))

    if args.output_format == "json":
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        print(result.to_markdown())

    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    """Build dependency graph from config."""
    from devkit.tools.config_reader import read_config
    from devkit.tools.graph_builder import build_config_graph

    config_path = Path(args.config_path) if args.config_path else detect_config()
    if not config_path or not config_path.exists():
        print("No OpenCode config found. Specify --config-path.")
        return 1

    result = read_config(config_path)
    if not result.success:
        print(f"Failed to read config: {'; '.join(result.errors)}")
        return 1

    graph = build_config_graph(result.config)
    output = {"graph": graph.to_dict()}

    if args.output_file:
        with open(args.output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Graph written to {args.output_file}")
        print(f"  Nodes: {len(graph.nodes)}  Edges: {len(graph.edges)}")
    else:
        print(json.dumps(output, indent=2))

    return 0


def main() -> int:
    load_dotenv()

    args = parse_args()

    if not args.command:
        print("Usage: devkit <command> [options]")
        print("\nCommands:")
        print("  analyze    Run full analysis pipeline")
        print("  audit      Run security audit")
        print("  score      Calculate health score")
        print("  history    View analysis history")
        print("  migrate    Migration assistant")
        print("  diff       Compare two configs")
        print("  graph      Build dependency graph")
        print("\nRun 'devkit <command> --help' for more information.")
        return 0

    handlers = {
        "analyze": cmd_analyze,
        "audit": cmd_audit,
        "score": cmd_score,
        "history": cmd_history,
        "migrate": cmd_migrate,
        "diff": cmd_diff,
        "graph": cmd_graph,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)

    print(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
