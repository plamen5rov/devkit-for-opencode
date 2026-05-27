"""Placeholder test to verify pytest infrastructure."""

from pathlib import Path


def test_project_root_exists(project_root: Path) -> None:
    """Verify the project root fixture works."""
    assert project_root.exists()
    assert (project_root / "pyproject.toml").exists()


def test_main_imports() -> None:
    """Verify the main module can be imported."""
    import devkit
    assert devkit.__version__ == "0.1.0"
