"""Unit tests for dependency and manifest auditor tool."""

import pytest
from pathlib import Path
from app.tools.dependency_auditor import (
    audit_dependencies,
    parse_declared_npm_deps,
    parse_declared_python_deps,
    extract_imported_js_packages,
    extract_imported_python_packages,
)


def test_audit_npm_dependencies(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"lodash": "^4.17.21", "unused-lib": "^1.0.0"}}', encoding="utf-8")

    src_file = tmp_path / "index.ts"
    src_file.write_text("import lodash from 'lodash';\nconsole.log(lodash);", encoding="utf-8")

    result = audit_dependencies(str(tmp_path))
    assert result["npm"]["declared_count"] == 2
    assert "lodash" in result["npm"]["declared"]
    assert "unused-lib" in result["npm"]["unused_dependencies"]
    assert "lodash" not in result["npm"]["unused_dependencies"]


def test_audit_python_dependencies(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("fastapi>=0.100.0\nunused_pkg==1.2.3\n", encoding="utf-8")

    py_file = tmp_path / "app.py"
    py_file.write_text("import fastapi\napp = fastapi.FastAPI()", encoding="utf-8")

    result = audit_dependencies(str(tmp_path))
    assert result["python"]["declared_count"] == 2
    assert "unused_pkg" in result["python"]["unused_dependencies"]
    assert "fastapi" not in result["python"]["unused_dependencies"]
