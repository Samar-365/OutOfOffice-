"""Fast code search and symbol reference finder tool.

Integrates ripgrep (rg) with an in-process regex search fallback to locate
symbol usages, callers, and candidate dead code across codebases.
"""

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.tools.ast_parser import build_symbol_table, extract_symbols_from_file

logger = logging.getLogger("outofoffice.tools.search")

IGNORE_DIRS: Set[str] = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".pytest_cache", "coverage", ".next"
}


class SearchMatch:
    """Represents an individual search match in a file."""

    def __init__(self, file_path: str, line_number: int, line_content: str, match_text: str):
        self.file_path = file_path
        self.line_number = line_number
        self.line_content = line_content.strip()
        self.match_text = match_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content,
            "match_text": self.match_text,
        }


def _has_ripgrep() -> bool:
    """Checks if ripgrep (rg) executable is available in PATH."""
    return shutil.which("rg") is not None


def search_code_ripgrep(
    repo_path: Path,
    pattern: str,
    glob_pattern: Optional[str] = None,
    case_sensitive: bool = True,
    is_regex: bool = False,
    max_results: int = 100,
) -> List[SearchMatch]:
    """Executes search using native ripgrep subprocess."""
    cmd = ["rg", "--json", "--max-count", str(max_results)]
    if not case_sensitive:
        cmd.append("-i")
    if not is_regex:
        cmd.append("-F")
    if glob_pattern:
        cmd.extend(["-g", glob_pattern])

    # Add ignore flags
    for d in IGNORE_DIRS:
        cmd.extend(["-g", f"!{d}/*"])

    cmd.extend([pattern, str(repo_path)])

    matches: List[SearchMatch] = []
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        for line in res.stdout.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    payload = data.get("data", {})
                    path_text = payload.get("path", {}).get("text", "")
                    line_num = payload.get("line_number", 0)
                    lines_text = payload.get("lines", {}).get("text", "")
                    rel_path = Path(path_text).relative_to(repo_path).as_posix()
                    matches.append(SearchMatch(file_path=rel_path, line_number=line_num, line_content=lines_text, match_text=pattern))
                    if len(matches) >= max_results:
                        break
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Ripgrep execution failed, falling back to python search: {e}")

    return matches


def search_code_python(
    repo_path: Path,
    pattern: str,
    glob_pattern: Optional[str] = None,
    case_sensitive: bool = True,
    is_regex: bool = False,
    max_results: int = 100,
) -> List[SearchMatch]:
    """In-process Python file search fallback when ripgrep is unavailable."""
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(pattern if is_regex else re.escape(pattern), flags)
    matches: List[SearchMatch] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for file_name in files:
            file_path = Path(root) / file_name
            if glob_pattern and not file_path.match(glob_pattern):
                continue

            # Only search text/source files under 1MB
            if file_path.stat().st_size > 1024 * 1024:
                continue

            try:
                rel_path = file_path.relative_to(repo_path).as_posix()
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        if regex.search(line):
                            matches.append(
                                SearchMatch(
                                    file_path=rel_path,
                                    line_number=line_idx,
                                    line_content=line,
                                    match_text=pattern,
                                )
                            )
                            if len(matches) >= max_results:
                                return matches
            except Exception:
                continue

    return matches


def search_code(
    repo_path_str: str,
    pattern: str,
    glob_pattern: Optional[str] = None,
    case_sensitive: bool = True,
    is_regex: bool = False,
    max_results: int = 100,
) -> List[Dict[str, Any]]:
    """Public search function routing to ripgrep if installed, or python crawler."""
    repo_path = Path(repo_path_str).resolve()
    if not repo_path.exists():
        return []

    if _has_ripgrep():
        matches = search_code_ripgrep(repo_path, pattern, glob_pattern, case_sensitive, is_regex, max_results)
        if matches:
            return [m.to_dict() for m in matches]

    matches = search_code_python(repo_path, pattern, glob_pattern, case_sensitive, is_regex, max_results)
    return [m.to_dict() for m in matches]


def find_symbol_references(
    repo_path_str: str,
    symbol_name: str,
    defining_file_rel_path: Optional[str] = None,
    defining_line_start: Optional[int] = None,
    defining_line_end: Optional[int] = None,
) -> Dict[str, Any]:
    """Searches for all references to a specific symbol across the codebase, excluding its definition."""
    repo_path = Path(repo_path_str).resolve()
    # Search word-bounded symbol
    pattern = rf"\b{re.escape(symbol_name)}\b"
    raw_matches = search_code_python(repo_path, pattern, is_regex=True, case_sensitive=True, max_results=200)

    external_references: List[SearchMatch] = []
    internal_references: List[SearchMatch] = []

    for m in raw_matches:
        # Check if match is on definition line in defining file
        if defining_file_rel_path and m.file_path == defining_file_rel_path:
            if defining_line_start and defining_line_end:
                if defining_line_start <= m.line_number <= defining_line_end:
                    continue  # Skip definition line itself
            internal_references.append(m)
        else:
            external_references.append(m)

    total_refs = len(external_references) + len(internal_references)

    return {
        "symbol_name": symbol_name,
        "defining_file": defining_file_rel_path,
        "total_references_count": total_refs,
        "external_references_count": len(external_references),
        "internal_references_count": len(internal_references),
        "is_unused_candidate": total_refs == 0,
        "external_references": [m.to_dict() for m in external_references[:10]],
    }


def find_dead_code_candidates(repo_path_str: str, max_check: int = 50) -> List[Dict[str, Any]]:
    """Analyzes exported AST symbols and tests for 0 cross-codebase references."""
    table = build_symbol_table(repo_path_str, max_files=100)
    symbols = table.get("symbols", [])
    candidates: List[Dict[str, Any]] = []

    # Check exported and top-level functions/classes
    checked = 0
    for sym in symbols:
        name = sym.get("name", "")
        if name in {"main", "init", "handler", "app", "__init__", "lifespan"}:
            continue  # Skip framework entrypoints

        ref_info = find_symbol_references(
            repo_path_str=repo_path_str,
            symbol_name=name,
            defining_file_rel_path=sym.get("file_path"),
            defining_line_start=sym.get("line_start"),
            defining_line_end=sym.get("line_end"),
        )

        if ref_info["is_unused_candidate"]:
            candidates.append({
                "symbol_name": name,
                "kind": sym.get("kind"),
                "file_path": sym.get("file_path"),
                "line_start": sym.get("line_start"),
                "line_end": sym.get("line_end"),
                "confidence": "HIGH" if sym.get("is_exported") else "MEDIUM",
                "evidence": f"0 callers found in repository for symbol '{name}'",
            })

        checked += 1
        if checked >= max_check:
            break

    return candidates
