"""Deterministic tools package for codebase intelligence, Git, AST, and testing."""
from .repo_discovery import discover_repository, validate_repository_path
from .ast_parser import CodeSymbol, extract_symbols_from_file, build_symbol_table
from .search_engine import search_code, find_symbol_references, find_dead_code_candidates

__all__ = [
    "discover_repository",
    "validate_repository_path",
    "CodeSymbol",
    "extract_symbols_from_file",
    "build_symbol_table",
    "search_code",
    "find_symbol_references",
    "find_dead_code_candidates",
]
