"""Surgical file patcher and in-memory rollback engine.

Applies line-bounded, deterministic code edits, verifies syntax post-patch,
generates unified diffs, and provides safe instant rollbacks.
"""

import ast
import difflib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("outofoffice.tools.patcher")

PROTECTED_FILES = {
    ".env",
    ".git",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
}


class PatchResult:
    """Structured result of a file patch operation."""

    def __init__(
        self,
        file_path: str,
        success: bool,
        diff_unified: str = "",
        error: Optional[str] = None,
        original_content: Optional[str] = None,
        patched_content: Optional[str] = None,
    ):
        self.file_path = file_path
        self.success = success
        self.diff_unified = diff_unified
        self.error = error
        self.original_content = original_content
        self.patched_content = patched_content

    def to_dict(self) -> Dict[str, Any]:
        """Serializes PatchResult to dictionary."""
        return {
            "file_path": self.file_path,
            "success": self.success,
            "diff_unified": self.diff_unified,
            "error": self.error,
        }


def _is_path_safe(file_rel_path: str, repo_root: Path) -> Tuple[bool, Path]:
    """Ensures file is inside the repository root and not a protected file."""
    # Prevent traversal attacks (../)
    target = (repo_root / file_rel_path).resolve()
    if not str(target).startswith(str(repo_root.resolve())):
        return False, target

    # Check protected files
    if target.name in PROTECTED_FILES:
        return False, target

    return True, target


def _verify_syntax_if_python(file_path: Path, new_content: str) -> Tuple[bool, Optional[str]]:
    """Verifies that new Python content is syntactically valid."""
    if file_path.suffix.lower() in [".py", ".pyi"]:
        try:
            ast.parse(new_content, filename=str(file_path))
        except SyntaxError as e:
            return False, f"SyntaxError introduced on line {e.lineno}: {e.msg}"
    return True, None


def generate_unified_diff(
    original_text: str,
    new_text: str,
    file_path: str,
) -> str:
    """Generates standard unified diff format string."""
    orig_lines = original_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    return "".join(diff)


def apply_surgical_patch(
    repo_path_str: str,
    file_rel_path: str,
    target_content: str,
    replacement_content: str,
    verify_syntax: bool = True,
) -> PatchResult:
    """Replaces exact target_content block with replacement_content in target file."""
    repo_root = Path(repo_path_str).resolve()
    is_safe, target_file = _is_path_safe(file_rel_path, repo_root)
    if not is_safe:
        return PatchResult(
            file_path=file_rel_path,
            success=False,
            error=f"Unsafe or protected file path: {file_rel_path}",
        )

    if not target_file.exists() or not target_file.is_file():
        return PatchResult(
            file_path=file_rel_path,
            success=False,
            error=f"Target file does not exist: {file_rel_path}",
        )

    try:
        original_text = target_file.read_text(encoding="utf-8")
    except Exception as e:
        return PatchResult(
            file_path=file_rel_path,
            success=False,
            error=f"Failed to read file: {e}",
        )

    # Normalize newlines for matching
    norm_orig = original_text.replace("\r\n", "\n")
    norm_target = target_content.replace("\r\n", "\n").strip()
    norm_replacement = replacement_content.replace("\r\n", "\n")

    if norm_target not in norm_orig:
        # Try line-trimmed matching
        target_lines = [l.strip() for l in norm_target.splitlines() if l.strip()]
        if not target_lines:
            return PatchResult(
                file_path=file_rel_path,
                success=False,
                error="Target content to replace cannot be empty.",
            )
        return PatchResult(
            file_path=file_rel_path,
            success=False,
            error=f"Target content block was not found verbatim in {file_rel_path}.",
        )

    # Count occurrences
    count = norm_orig.count(norm_target)
    if count > 1:
        return PatchResult(
            file_path=file_rel_path,
            success=False,
            error=f"Target content matches {count} different locations. Ambiguous replacement aborted.",
        )

    # Apply replacement
    patched_text = norm_orig.replace(norm_target, norm_replacement, 1)

    # Syntax verification
    if verify_syntax:
        is_valid_syntax, syn_err = _verify_syntax_if_python(target_file, patched_text)
        if not is_valid_syntax:
            return PatchResult(
                file_path=file_rel_path,
                success=False,
                error=f"Patch rejected: {syn_err}",
                original_content=original_text,
            )

    # Generate unified diff
    diff_str = generate_unified_diff(original_text, patched_text, file_rel_path)

    # Write to disk
    try:
        target_file.write_text(patched_text, encoding="utf-8")
        return PatchResult(
            file_path=file_rel_path,
            success=True,
            diff_unified=diff_str,
            original_content=original_text,
            patched_content=patched_text,
        )
    except Exception as e:
        return PatchResult(
            file_path=file_rel_path,
            success=False,
            error=f"Failed to write patched file: {e}",
        )


def rollback_patch(
    repo_path_str: str,
    file_rel_path: str,
    original_content: str,
) -> bool:
    """Restores the original file contents cleanly."""
    repo_root = Path(repo_path_str).resolve()
    target_file = (repo_root / file_rel_path).resolve()
    if target_file.exists():
        try:
            target_file.write_text(original_content, encoding="utf-8")
            return True
        except Exception:
            return False
    return False
