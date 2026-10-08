"""Unit tests for repository discovery and metadata extraction tool."""

import pytest
from pathlib import Path
from app.tools.repo_discovery import (
    discover_repository,
    validate_repository_path,
    detect_manifests_and_frameworks,
    index_source_files,
)


def test_validate_current_workspace():
    current_dir = Path(__file__).resolve().parent.parent.parent
    is_valid, msg, path = validate_repository_path(str(current_dir))
    assert is_valid is True
    assert path.exists()


def test_validate_nonexistent_directory():
    is_valid, msg, _ = validate_repository_path("C:/nonexistent_directory_12345")
    assert is_valid is False
    assert "does not exist" in msg


def test_discover_current_repository():
    current_dir = str(Path(__file__).resolve().parent.parent.parent)
    meta = discover_repository(current_dir)
    assert meta["is_valid"] is True
    assert "Python" in meta["detected_languages"]
    assert any("requirements.txt" in m for m in meta["manifest_files"])
    assert meta["test_framework"] == "pytest"
    assert meta["file_count"] > 5
    assert meta["git"]["current_branch"] == "main"
