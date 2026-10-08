"""AST and symbol parser for Python, TypeScript, and JavaScript.

Extracts functions, classes, interfaces, methods, and export definitions
to construct codebase symbol tables and detect potential dead code.
"""

import ast
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("outofoffice.tools.ast")


class CodeSymbol:
    """Represents a structured code declaration (function, class, interface, export)."""

    def __init__(
        self,
        name: str,
        kind: str,  # function, async_function, class, interface, type_alias, variable
        file_path: str,
        line_start: int,
        line_end: int,
        is_exported: bool = False,
        docstring: Optional[str] = None,
        parameters: Optional[List[str]] = None,
    ):
        self.name = name
        self.kind = kind
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.is_exported = is_exported
        self.docstring = docstring
        self.parameters = parameters or []

    def to_dict(self) -> Dict[str, Any]:
        """Serializes symbol to dictionary."""
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "is_exported": self.is_exported,
            "docstring": self.docstring,
            "parameters": self.parameters,
        }


# ----------------------------------------------------------------------
# Python AST Parsing (Native Python ast module)
# ----------------------------------------------------------------------

class PythonSymbolVisitor(ast.NodeVisitor):
    """AST visitor extracting Python classes, functions, and module-level symbols."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: List[CodeSymbol] = []
        self._scope_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Top-level or class-level method
        doc = ast.get_docstring(node)
        params = [a.arg for a in node.args.args]
        is_exported = not node.name.startswith("_")

        self.symbols.append(
            CodeSymbol(
                name=node.name,
                kind="function",
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                is_exported=is_exported and self._scope_depth == 0,
                docstring=doc,
                parameters=params,
            )
        )
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        doc = ast.get_docstring(node)
        params = [a.arg for a in node.args.args]
        is_exported = not node.name.startswith("_")

        self.symbols.append(
            CodeSymbol(
                name=node.name,
                kind="async_function",
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                is_exported=is_exported and self._scope_depth == 0,
                docstring=doc,
                parameters=params,
            )
        )
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef):
        doc = ast.get_docstring(node)
        is_exported = not node.name.startswith("_")

        self.symbols.append(
            CodeSymbol(
                name=node.name,
                kind="class",
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                is_exported=is_exported and self._scope_depth == 0,
                docstring=doc,
            )
        )
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1


def parse_python_file(file_path: Path, rel_path: str) -> List[CodeSymbol]:
    """Parses a Python file using native AST."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))
        visitor = PythonSymbolVisitor(rel_path)
        visitor.visit(tree)
        return visitor.symbols
    except Exception as e:
        logger.debug(f"Failed to parse Python AST for {rel_path}: {e}")
        return []


# ----------------------------------------------------------------------
# TypeScript / JavaScript Parsing (Regex / Pattern Tokenizer)
# ----------------------------------------------------------------------

# Patterns for TS/JS declarations
TS_EXPORT_FN_RE = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)",
    re.MULTILINE,
)
TS_EXPORT_CONST_FN_RE = re.compile(
    r"export\s+const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*(?:=>|:)",
    re.MULTILINE,
)
TS_EXPORT_CLASS_RE = re.compile(
    r"export\s+(?:default\s+)?class\s+([A-Za-z0-9_$]+)",
    re.MULTILINE,
)
TS_EXPORT_INTERFACE_RE = re.compile(
    r"export\s+interface\s+([A-Za-z0-9_$]+)",
    re.MULTILINE,
)
TS_EXPORT_TYPE_RE = re.compile(
    r"export\s+type\s+([A-Za-z0-9_$]+)",
    re.MULTILINE,
)
TS_LOCAL_FN_RE = re.compile(
    r"^(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)",
    re.MULTILINE,
)


def parse_typescript_javascript_file(file_path: Path, rel_path: str) -> List[CodeSymbol]:
    """Parses TypeScript/JavaScript files for exported and local functions, classes, and types."""
    symbols: List[CodeSymbol] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            clean = line.strip()
            if not clean or clean.startswith("//") or clean.startswith("/*") or clean.startswith("*"):
                continue

            # Exported function
            m = TS_EXPORT_FN_RE.search(line)
            if m:
                name = m.group(1)
                params = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]
                symbols.append(CodeSymbol(name=name, kind="function", file_path=rel_path, line_start=idx, line_end=idx, is_exported=True, parameters=params))
                continue

            # Exported const arrow function
            m = TS_EXPORT_CONST_FN_RE.search(line)
            if m:
                name = m.group(1)
                params = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]
                symbols.append(CodeSymbol(name=name, kind="function", file_path=rel_path, line_start=idx, line_end=idx, is_exported=True, parameters=params))
                continue

            # Exported class
            m = TS_EXPORT_CLASS_RE.search(line)
            if m:
                name = m.group(1)
                symbols.append(CodeSymbol(name=name, kind="class", file_path=rel_path, line_start=idx, line_end=idx, is_exported=True))
                continue

            # Exported interface
            m = TS_EXPORT_INTERFACE_RE.search(line)
            if m:
                name = m.group(1)
                symbols.append(CodeSymbol(name=name, kind="interface", file_path=rel_path, line_start=idx, line_end=idx, is_exported=True))
                continue

            # Exported type
            m = TS_EXPORT_TYPE_RE.search(line)
            if m:
                name = m.group(1)
                symbols.append(CodeSymbol(name=name, kind="type_alias", file_path=rel_path, line_start=idx, line_end=idx, is_exported=True))
                continue

            # Local function
            m = TS_LOCAL_FN_RE.search(line)
            if m and not line.startswith("export"):
                name = m.group(1)
                params = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]
                symbols.append(CodeSymbol(name=name, kind="function", file_path=rel_path, line_start=idx, line_end=idx, is_exported=False, parameters=params))

    except Exception as e:
        logger.debug(f"Failed to parse TS/JS file {rel_path}: {e}")

    return symbols


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

def extract_symbols_from_file(file_path: Path, repo_root: Path) -> List[CodeSymbol]:
    """Extracts symbols from a single source file based on extension."""
    if not file_path.exists() or not file_path.is_file():
        return []

    rel_path = file_path.relative_to(repo_root).as_posix()
    ext = file_path.suffix.lower()

    if ext in {".py", ".pyi"}:
        return parse_python_file(file_path, rel_path)
    elif ext in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        return parse_typescript_javascript_file(file_path, rel_path)

    return []


def build_symbol_table(repo_path_str: str, max_files: int = 300) -> Dict[str, Any]:
    """Scans all source files in repository and constructs global symbol mapping."""
    repo_root = Path(repo_path_str).resolve()
    if not repo_root.exists():
        return {"total_symbols": 0, "symbols": []}

    ignore_dirs = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
    all_symbols: List[CodeSymbol] = []
    processed_count = 0

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

        for file_name in files:
            file_path = Path(root) / file_name
            ext = file_path.suffix.lower()

            if ext in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                syms = extract_symbols_from_file(file_path, repo_root)
                all_symbols.extend(syms)
                processed_count += 1

                if processed_count >= max_files:
                    break
        if processed_count >= max_files:
            break

    return {
        "total_symbols": len(all_symbols),
        "exported_symbols_count": sum(1 for s in all_symbols if s.is_exported),
        "symbols": [s.to_dict() for s in all_symbols],
    }
