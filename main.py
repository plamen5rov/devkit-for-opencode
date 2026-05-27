"""DevKit for OpenCode — Entry point.

Usage:
    python main.py                  # Run default analysis
    python main.py --config PATH    # Analyze specific config
    python main.py --mode audit     # Run security audit
    python main.py --mode score     # Calculate health score
    python main.py --help           # Show help
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DevKit for OpenCode — Analyze and optimize OpenCode configurations",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to opencode.json config file (default: auto-detect)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["analyze", "audit", "score", "security", "token"],
        default="analyze",
        help="Analysis mode (default: analyze)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Generate fixed config (audit mode only)",
    )
    return parser.parse_args()


def detect_config() -> Optional[Path]:
    """Auto-detect OpenCode config file."""
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


def run_analyze(config_path: Path, verbose: bool) -> int:
    """Run full analysis pipeline."""
    from devkit.tasks.full_audit import create_full_audit_task

    report = create_full_audit_task(str(config_path))
    print(json.dumps(report.to_dict(), indent=2, default=str))
    return 0


def run_audit(config_path: Path, verbose: bool, fix: bool) -> int:
    """Run security audit."""
    from devkit.tasks.security_scan import run_security_scan

    result = run_security_scan(str(config_path))
    if verbose:
        print(result.to_markdown())
    else:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0


def run_score(config_path: Path, verbose: bool) -> int:
    """Calculate health score."""
    from devkit.agents.orchestrator import run_orchestration

    result = run_orchestration(str(config_path))
    score = result.summary.get("health_score", 0)

    if verbose:
        print(f"Health Score: {score}/100")
        print(f"\nBreakdown:")
        print(f"  Issues: {result.summary.get('total_issues', 0)}")
        print(f"  Warnings: {result.summary.get('total_warnings', 0)}")
        print(f"  Agents: {result.summary.get('agent_count', 0)}")
        print(f"  Skills: {result.summary.get('skill_count', 0)}")
        print(f"  MCP Servers: {result.summary.get('mcp_count', 0)}")
        print(f"  Commands: {result.summary.get('command_count', 0)}")
        print(f"  MCP Token Estimate: ~{result.summary.get('mcp_token_estimate', 0)} tokens")
    else:
        print(json.dumps({"health_score": score, "summary": result.summary}, indent=2))
    return 0


def run_security(config_path: Path, verbose: bool) -> int:
    """Run security scan only."""
    return run_audit(config_path, verbose, fix=False)


def run_token(config_path: Path, verbose: bool) -> int:
    """Run token optimization analysis."""
    from devkit.tasks.token_optimization import run_token_analysis

    report = run_token_analysis(str(config_path))
    if verbose:
        print(report.to_markdown())
    else:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    return 0


def main() -> int:
    load_dotenv()

    args = parse_args()

    config_path = Path(args.config) if args.config else detect_config()

    if not config_path or not config_path.exists():
        print("No OpenCode config found. Specify --config or place opencode.json in .opencode/")
        return 1

    if args.verbose:
        print(f"Analyzing config: {config_path}")
        print(f"Mode: {args.mode}")

    mode_handlers = {
        "analyze": lambda: run_analyze(config_path, args.verbose),
        "audit": lambda: run_audit(config_path, args.verbose, args.fix),
        "score": lambda: run_score(config_path, args.verbose),
        "security": lambda: run_security(config_path, args.verbose),
        "token": lambda: run_token(config_path, args.verbose),
    }

    handler = mode_handlers.get(args.mode)
    if handler:
        return handler()

    print(f"Unknown mode: {args.mode}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
