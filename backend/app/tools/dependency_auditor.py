"""Dependency & manifest inspector tool for JavaScript/TypeScript and Python projects.

Cross-references declared manifest packages against actual source code imports
to identify unused and missing dependencies.
"""

import ast
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

logger = logging.getLogger("outofoffice.tools.deps")

IGNORE_DIRS: Set[str] = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".pytest_cache", ".next", "coverage"
}

# Standard built-in Python modules to ignore when checking third-party dependencies
PYTHON_BUILTINS: Set[str] = {
    "os", "sys", "re", "json", "time", "datetime", "math", "random", "typing",
    "collections", "itertools", "functools", "pathlib", "subprocess", "shutil",
    "logging", "threading", "asyncio", "unittest", "tempfile", "io", "csv",
    "http", "urllib", "hashlib", "base64", "uuid", "copy", "socket", "contextlib",
    "dataclasses", "enum", "inspect", "abc", "typing_extensions",
}

# Standard Node.js built-in modules
NODE_BUILTINS: Set[str] = {
    "fs", "fs/promises", "path", "os", "http", "https", "url", "crypto",
    "events", "util", "stream", "buffer", "child_process", "cluster", "net",
    "process", "querystring", "readline", "tls", "zlib", "assert",
}


def parse_declared_npm_deps(repo_path: Path) -> Dict[str, str]:
    """Extracts declared dependencies from package.json files."""
    declared: Dict[str, str] = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        if "package.json" in files:
            pkg_path = Path(root) / "package.json"
            try:
                data = json.loads(pkg_path.read_text(encoding="utf-8", errors="ignore"))
                deps = data.get("dependencies", {})
                for dep, ver in deps.items():
                    declared[dep] = ver
            except Exception as e:
                logger.debug(f"Error parsing package.json at {pkg_path}: {e}")
    return declared


def parse_declared_python_deps(repo_path: Path) -> Dict[str, str]:
    """Extracts declared dependencies from requirements.txt and pyproject.toml."""
    declared: Dict[str, str] = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        # requirements.txt
        for f in files:
            if f.endswith(".txt") and "requirement" in f.lower():
                req_path = Path(root) / f
                try:
                    for line in req_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                        clean = line.split("#")[0].strip()
                        if clean and not clean.startswith("-"):
                            pkg = re.split(r"[><=~;!]", clean)[0].strip()
                            if pkg:
                                declared[pkg.lower().replace("-", "_")] = clean
                except Exception:
                    pass

        # pyproject.toml
        if "pyproject.toml" in files:
            pyproj = Path(root) / "pyproject.toml"
            try:
                content = pyproj.read_text(encoding="utf-8", errors="ignore")
                # Simple extraction of dependencies list
                in_deps = False
                for line in content.splitlines():
                    clean = line.strip()
                    if "dependencies" in clean and "=" in clean:
                        in_deps = True
                        continue
                    if in_deps:
                        if clean.startswith("]"):
                            in_deps = False
                            continue
                        dep_name = clean.strip("\"',")
                        if dep_name:
                            pkg = re.split(r"[><=~;!]", dep_name)[0].strip()
                            if pkg:
                                declared[pkg.lower().replace("-", "_")] = dep_name
            except Exception:
                pass

    return declared


def extract_imported_js_packages(repo_path: Path) -> Set[str]:
    """Extracts imported package names from JS/TS source files."""
    imported: Set[str] = set()
    # import ... from 'pkg' or require('pkg')
    js_import_re = re.compile(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\))""")

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file_name in files:
            if file_name.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs")):
                file_path = Path(root) / file_name
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for m in js_import_re.finditer(content):
                        specifier = m.group(1) or m.group(2)
                        if specifier and not specifier.startswith("."):
                            # Handle scoped packages (e.g. @sentry/node) vs standard
                            parts = specifier.split("/")
                            pkg_name = f"{parts[0]}/{parts[1]}" if specifier.startswith("@") and len(parts) > 1 else parts[0]
                            if pkg_name not in NODE_BUILTINS:
                                imported.add(pkg_name)
                except Exception:
                    continue
    return imported


def extract_imported_python_packages(repo_path: Path) -> Set[str]:
    """Extracts imported top-level package names from Python source files."""
    imported: Set[str] = set()

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file_name in files:
            if file_name.endswith((".py", ".pyi")):
                file_path = Path(root) / file_name
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    tree = ast.parse(content, filename=str(file_path))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                top_pkg = alias.name.split(".")[0].lower()
                                if top_pkg not in PYTHON_BUILTINS:
                                    imported.add(top_pkg)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and node.level == 0:
                                top_pkg = node.module.split(".")[0].lower()
                                if top_pkg not in PYTHON_BUILTINS:
                                    imported.add(top_pkg)
                except Exception:
                    continue
    return imported


def audit_dependencies(repo_path_str: str) -> Dict[str, Any]:
    """Audits dependencies across the repository and returns unused and active packages."""
    repo_path = Path(repo_path_str).resolve()
    if not repo_path.exists():
        return {"error": f"Path not found: {repo_path_str}"}

    # 1. NPM Auditing
    declared_npm = parse_declared_npm_deps(repo_path)
    imported_npm = extract_imported_js_packages(repo_path)
    unused_npm: List[str] = []
    for dep in declared_npm:
        if dep not in imported_npm:
            unused_npm.append(dep)

    # 2. Python Auditing
    declared_py = parse_declared_python_deps(repo_path)
    imported_py = extract_imported_python_packages(repo_path)
    unused_py: List[str] = []
    for dep in declared_py:
        if dep not in imported_py and dep.replace("-", "_") not in imported_py:
            unused_py.append(dep)

    return {
        "npm": {
            "declared_count": len(declared_npm),
            "imported_count": len(imported_npm),
            "unused_dependencies": unused_npm,
            "declared": list(declared_npm.keys()),
        },
        "python": {
            "declared_count": len(declared_py),
            "imported_count": len(imported_py),
            "unused_dependencies": unused_py,
            "declared": list(declared_py.keys()),
        },
        "total_unused_count": len(unused_npm) + len(unused_py),
    }
