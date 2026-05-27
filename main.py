"""DevKit for OpenCode — Entry point.

Usage:
    python main.py                  # Run default analysis
    python main.py --config PATH    # Analyze specific config
    python main.py --help           # Show help
"""

from __future__ import annotations

import argparse
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
        choices=["analyze", "audit", "score"],
        default="analyze",
        help="Analysis mode (default: analyze)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
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

    print(f"DevKit for OpenCode v0.1.0")
    print(f"Config: {config_path}")
    print("Analysis pipeline ready. Implement Phase 2 tools to enable full analysis.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
