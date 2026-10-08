"""Repository discovery, file indexing, language detection, and manifest analysis tool.

Inspects local repositories to provide deterministic context to the LangGraph agent.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("outofoffice.tools.discovery")

IGNORE_DIRS: Set[str] = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    "coverage",
    ".idea",
    ".vscode",
    "target",  # Rust
    "vendor",  # Go/PHP
}

SOURCE_EXTENSIONS: Set[str] = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".pyi",
    ".rs",
    ".go",
    ".java", ".kt",
    ".c", ".cpp", ".h", ".hpp",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".md",
}


def validate_repository_path(raw_path: str) -> Tuple[bool, str, Path]:
    """Validates if a given path is an accessible local Git directory."""
    if not raw_path or not raw_path.strip():
        return False, "Repository path cannot be empty.", Path()

    path = Path(raw_path.strip()).resolve()
    if not path.exists():
        return False, f"Directory does not exist: {path}", path
    if not path.is_dir():
        return False, f"Path is not a directory: {path}", path
    if not (path / ".git").exists():
        return False, f"Directory is not a Git repository (.git folder not found): {path}", path

    return True, "Valid Git repository", path


def get_git_info(repo_path: Path) -> Dict[str, Any]:
    """Extracts branch, commit, and working tree status from Git."""
    info: Dict[str, Any] = {
        "current_branch": "main",
        "head_commit": "",
        "has_uncommitted_changes": False,
        "uncommitted_files": [],
        "remote_url": "",
    }
    try:
        # Branch
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            info["current_branch"] = res.stdout.strip()

        # Commit
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            info["head_commit"] = res.stdout.strip()[:8]

        # Status
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().splitlines()
            info["has_uncommitted_changes"] = True
            info["uncommitted_files"] = [line[3:].strip() for line in lines[:20]]

        # Remote
        res = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            info["remote_url"] = res.stdout.strip()

    except Exception as e:
        logger.warning(f"Git inspection error: {e}")

    return info


def detect_manifests_and_frameworks(repo_path: Path) -> Dict[str, Any]:
    """Inspects root and top-level manifest files to detect languages, frameworks, and test scripts."""
    manifests: List[str] = []
    detected_languages: Set[str] = set()
    frameworks: List[str] = []
    test_framework = "None"
    test_command = ""
    dependencies: List[str] = []

    # Check root and 1-level deep subdirectories (e.g. backend/, frontend/, src/, server/)
    candidate_dirs = [repo_path]
    try:
        for child in repo_path.iterdir():
            if child.is_dir() and child.name not in IGNORE_DIRS and not child.name.startswith("."):
                candidate_dirs.append(child)
    except Exception:
        pass

    for d in candidate_dirs:
        # 1. JavaScript / TypeScript
        pkg_json_path = d / "package.json"
        if pkg_json_path.exists():
            rel_manifest = pkg_json_path.relative_to(repo_path).as_posix()
            if rel_manifest not in manifests:
                manifests.append(rel_manifest)
            detected_languages.add("JavaScript")
            if (d / "tsconfig.json").exists() or (repo_path / "tsconfig.json").exists():
                detected_languages.add("TypeScript")

            try:
                content = json.loads(pkg_json_path.read_text(encoding="utf-8", errors="ignore"))
                scripts = content.get("scripts", {})
                deps = {**content.get("dependencies", {}), **content.get("devDependencies", {})}
                dependencies.extend(list(deps.keys()))

                # Frameworks
                if "react" in deps and "React" not in frameworks:
                    frameworks.append("React")
                if "next" in deps and "Next.js" not in frameworks:
                    frameworks.append("Next.js")
                if "vue" in deps and "Vue" not in frameworks:
                    frameworks.append("Vue")
                if "svelte" in deps and "Svelte" not in frameworks:
                    frameworks.append("Svelte")
                if "express" in deps and "Express" not in frameworks:
                    frameworks.append("Express")
                if "fastify" in deps and "Fastify" not in frameworks:
                    frameworks.append("Fastify")
                if ("nest" in deps or "@nestjs/core" in deps) and "NestJS" not in frameworks:
                    frameworks.append("NestJS")

                # Tests
                if "vitest" in deps or "vitest" in scripts.get("test", ""):
                    test_framework = "Vitest"
                    test_command = "npm run test" if "test" in scripts else "npx vitest run"
                elif "jest" in deps or "jest" in scripts.get("test", ""):
                    test_framework = "Jest"
                    test_command = "npm test"
                elif "mocha" in deps:
                    test_framework = "Mocha"
                    test_command = "npx mocha"
                elif "test" in scripts and test_framework == "None":
                    test_framework = "npm test"
                    test_command = "npm test"
            except Exception as e:
                logger.warning(f"Error parsing package.json at {pkg_json_path}: {e}")

        # 2. Python
        pyproject_path = d / "pyproject.toml"
        req_txt_path = d / "requirements.txt"
        setup_py_path = d / "setup.py"

        if pyproject_path.exists() or req_txt_path.exists() or setup_py_path.exists():
            detected_languages.add("Python")
            if pyproject_path.exists():
                rel_pyproj = pyproject_path.relative_to(repo_path).as_posix()
                if rel_pyproj not in manifests:
                    manifests.append(rel_pyproj)
            if req_txt_path.exists():
                rel_req = req_txt_path.relative_to(repo_path).as_posix()
                if rel_req not in manifests:
                    manifests.append(rel_req)
            if setup_py_path.exists():
                rel_setup = setup_py_path.relative_to(repo_path).as_posix()
                if rel_setup not in manifests:
                    manifests.append(rel_setup)

            all_py_text = ""
            if pyproject_path.exists():
                all_py_text += pyproject_path.read_text(encoding="utf-8", errors="ignore")
            if req_txt_path.exists():
                all_py_text += req_txt_path.read_text(encoding="utf-8", errors="ignore")

            if "fastapi" in all_py_text.lower() and "FastAPI" not in frameworks:
                frameworks.append("FastAPI")
            if "django" in all_py_text.lower() and "Django" not in frameworks:
                frameworks.append("Django")
            if "flask" in all_py_text.lower() and "Flask" not in frameworks:
                frameworks.append("Flask")
            if ("langchain" in all_py_text.lower() or "langgraph" in all_py_text.lower()) and "LangGraph/LangChain" not in frameworks:
                frameworks.append("LangGraph/LangChain")

            if test_framework == "None":
                test_framework = "pytest"
                test_command = "pytest"

        # 3. Rust
        cargo_path = d / "Cargo.toml"
        if cargo_path.exists():
            rel_cargo = cargo_path.relative_to(repo_path).as_posix()
            if rel_cargo not in manifests:
                manifests.append(rel_cargo)
            detected_languages.add("Rust")
            if "Cargo" not in frameworks:
                frameworks.append("Cargo")
            if test_framework == "None":
                test_framework = "cargo test"
                test_command = "cargo test"

        # 4. Go
        go_mod_path = d / "go.mod"
        if go_mod_path.exists():
            rel_go = go_mod_path.relative_to(repo_path).as_posix()
            if rel_go not in manifests:
                manifests.append(rel_go)
            detected_languages.add("Go")
            if "Go Modules" not in frameworks:
                frameworks.append("Go Modules")
            if test_framework == "None":
                test_framework = "go test"
                test_command = "go test ./..."

    # Formulate project title
    proj_type = " / ".join(frameworks) if frameworks else (" / ".join(detected_languages) if detected_languages else "Generic Codebase")

    return {
        "manifest_files": manifests,
        "detected_languages": sorted(list(detected_languages)),
        "frameworks": frameworks,
        "project_type": proj_type,
        "test_framework": test_framework,
        "test_command": test_command,
        "dependencies_sample": dependencies[:25],
    }


def index_source_files(repo_path: Path, max_files: int = 500) -> Dict[str, Any]:
    """Recursively indexes source files, categorizing extensions and estimating lines of code."""
    file_list: List[Dict[str, Any]] = []
    extension_counts: Dict[str, int] = {}
    total_loc = 0

    for root, dirs, files in os.walk(repo_path):
        # Exclude ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for file_name in sorted(files):
            file_path = Path(root) / file_name
            ext = file_path.suffix.lower()

            if ext in SOURCE_EXTENSIONS or file_name in {"Makefile", "Dockerfile", "Containerfile"}:
                rel_path = file_path.relative_to(repo_path).as_posix()
                size = file_path.stat().st_size
                loc = 0

                # Count lines of code if under 500KB
                if size < 500 * 1024:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            loc = sum(1 for _ in f)
                            total_loc += loc
                    except Exception:
                        pass

                file_list.append({
                    "relative_path": rel_path,
                    "extension": ext,
                    "size_bytes": size,
                    "loc": loc,
                })
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

                if len(file_list) >= max_files:
                    break
        if len(file_list) >= max_files:
            break

    return {
        "total_source_files": len(file_list),
        "total_estimated_loc": total_loc,
        "extension_counts": extension_counts,
        "files": file_list,
    }


def discover_repository(repo_path_str: str) -> Dict[str, Any]:
    """High-level repository discovery tool combining Git, manifests, and file indexing."""
    is_valid, msg, path = validate_repository_path(repo_path_str)
    if not is_valid:
        return {"is_valid": False, "error": msg, "repo_path": repo_path_str}

    git_meta = get_git_info(path)
    proj_meta = detect_manifests_and_frameworks(path)
    file_meta = index_source_files(path)

    return {
        "is_valid": True,
        "repo_path": str(path),
        "repo_name": path.name,
        "git": git_meta,
        **proj_meta,
        **file_meta,
        "file_count": file_meta["total_source_files"],
    }
