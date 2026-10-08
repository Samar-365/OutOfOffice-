"""Repository inspection and discovery API routes."""

import os
import subprocess
from pathlib import Path
from typing import List, Tuple
from fastapi import APIRouter, HTTPException, status

from app.api.schemas import RepoValidateRequest, RepoValidateResponse

router = APIRouter(prefix="/repo", tags=["Repository"])


def _inspect_git_status(repo_path: Path) -> Tuple[bool, str, bool]:
    """Inspects Git repository status."""
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return False, "", False

    try:
        # Get active branch
        branch_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        current_branch = branch_res.stdout.strip() if branch_res.returncode == 0 else "main"

        # Check for uncommitted changes
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_uncommitted = bool(status_res.stdout.strip()) if status_res.returncode == 0 else False

        return True, current_branch, has_uncommitted
    except Exception:
        return True, "main", False


def _detect_project_metadata(repo_path: Path) -> Tuple[List[str], str, List[str], str, int]:
    """Scans repository root manifests and files to detect languages and frameworks."""
    manifests: List[str] = []
    languages: List[str] = []
    project_type = "Unknown"
    test_framework = "None"
    file_count = 0

    # Common manifest checks
    pkg_json = repo_path / "package.json"
    pyproject = repo_path / "pyproject.toml"
    req_txt = repo_path / "requirements.txt"
    cargo = repo_path / "Cargo.toml"
    go_mod = repo_path / "go.mod"

    if pkg_json.exists():
        manifests.append("package.json")
        languages.append("JavaScript/TypeScript")
        try:
            content = pkg_json.read_text(encoding="utf-8", errors="ignore")
            if "react" in content:
                project_type = "React"
            elif "next" in content:
                project_type = "Next.js"
            elif "vue" in content:
                project_type = "Vue"
            elif "express" in content:
                project_type = "Node.js (Express)"
            else:
                project_type = "Node.js"

            if "vitest" in content:
                test_framework = "Vitest"
            elif "jest" in content:
                test_framework = "Jest"
            elif "mocha" in content:
                test_framework = "Mocha"
            elif '"test"' in content:
                test_framework = "npm test"
        except Exception:
            project_type = "Node.js"

    if pyproject.exists() or req_txt.exists():
        if pyproject.exists():
            manifests.append("pyproject.toml")
        if req_txt.exists():
            manifests.append("requirements.txt")
        if "Python" not in languages:
            languages.append("Python")

        project_type = "Python" if project_type == "Unknown" else f"{project_type} + Python"
        test_framework = "pytest" if test_framework == "None" else test_framework

    if cargo.exists():
        manifests.append("Cargo.toml")
        languages.append("Rust")
        project_type = "Rust Cargo"
        test_framework = "cargo test"

    if go_mod.exists():
        manifests.append("go.mod")
        languages.append("Go")
        project_type = "Go Module"
        test_framework = "go test"

    # Count files (ignoring common build and version control folders)
    ignore_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".cache"}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        file_count += len(files)

    return languages, project_type, manifests, test_framework, file_count


@router.post("/validate", response_model=RepoValidateResponse)
async def validate_repository(payload: RepoValidateRequest):
    """Validates local directory existence, Git integrity, and framework metadata."""
    raw_path = payload.repo_path.strip()
    if not raw_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository path cannot be empty.")

    repo_path = Path(raw_path).resolve()
    if not repo_path.exists():
        return RepoValidateResponse(
            is_valid=False,
            repo_path=str(repo_path),
            is_git_repo=False,
            message=f"Directory does not exist: {repo_path}",
        )

    if not repo_path.is_dir():
        return RepoValidateResponse(
            is_valid=False,
            repo_path=str(repo_path),
            is_git_repo=False,
            message=f"Path is not a directory: {repo_path}",
        )

    # Inspect Git
    is_git, branch, has_uncommitted = _inspect_git_status(repo_path)
    if not is_git:
        return RepoValidateResponse(
            is_valid=False,
            repo_path=str(repo_path),
            is_git_repo=False,
            message="Directory exists, but is not an initialized Git repository (.git not found).",
        )

    # Inspect Language and Manifests
    languages, project_type, manifests, test_framework, file_count = _detect_project_metadata(repo_path)

    return RepoValidateResponse(
        is_valid=True,
        repo_path=str(repo_path),
        is_git_repo=True,
        current_branch=branch,
        has_uncommitted_changes=has_uncommitted,
        detected_languages=languages,
        project_type=project_type,
        manifest_files=manifests,
        test_framework=test_framework,
        file_count=file_count,
        message="Repository verified and ready for autonomous agent execution.",
    )
