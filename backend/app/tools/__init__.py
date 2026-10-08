"""Deterministic tools package for codebase intelligence, Git, AST, and testing."""
from .repo_discovery import discover_repository, validate_repository_path
from .ast_parser import CodeSymbol, extract_symbols_from_file, build_symbol_table
from .search_engine import search_code, find_symbol_references, find_dead_code_candidates
from .dependency_auditor import audit_dependencies
from .git_manager import GitManager
from .test_runner import TestResult, run_test_suite
from .linter_runner import LintIssue, run_static_analysis
from .patcher import PatchResult, apply_surgical_patch, rollback_patch, generate_unified_diff

__all__ = [
    "discover_repository",
    "validate_repository_path",
    "CodeSymbol",
    "extract_symbols_from_file",
    "build_symbol_table",
    "search_code",
    "find_symbol_references",
    "find_dead_code_candidates",
    "audit_dependencies",
    "GitManager",
    "TestResult",
    "run_test_suite",
    "LintIssue",
    "run_static_analysis",
    "PatchResult",
    "apply_surgical_patch",
    "rollback_patch",
    "generate_unified_diff",
]
