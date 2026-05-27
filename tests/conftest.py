"""Shared test fixtures and configuration."""

import pytest
from pathlib import Path

@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent

@pytest.fixture
def sample_config_path(project_root: Path) -> Path:
    """Return path to sample config for testing."""
    return project_root / "examples" / "good-config.json"
