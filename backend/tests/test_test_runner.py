"""Unit tests for test framework runner and output parser."""

import pytest
from pathlib import Path
from app.tools.test_runner import (
    TestResult,
    parse_pytest_output,
    parse_jest_vitest_output,
    run_test_suite,
)


def test_parse_pytest_output():
    mock_stdout = """
============================= test session starts =============================
backend/tests/test_api.py::test_health PASSED                            [ 50%]
backend/tests/test_api.py::test_fail FAILED                              [100%]
================================== FAILURES ===================================
__________________________________ test_fail __________________________________
FAILED backend/tests/test_api.py::test_fail - AssertionError: assert False
======================== 1 failed, 1 passed in 0.42s =========================
"""
    passed, failed, skipped, failing_tests = parse_pytest_output(mock_stdout)
    assert passed == 1
    assert failed == 1
    assert skipped == 0
    assert len(failing_tests) == 1
    assert failing_tests[0]["test_name"] == "test_fail"


def test_parse_jest_vitest_output():
    mock_stdout = """
 ✓ src/utils.test.ts (2 tests) 14ms
 ✕ src/auth.test.ts (1 test) 8ms
FAIL src/auth.test.ts
Tests: 1 failed, 2 passed, 3 total
Time: 1.25s
"""
    passed, failed, skipped, failing_tests = parse_jest_vitest_output(mock_stdout)
    assert passed == 2
    assert failed == 1
    assert skipped == 0
    assert len(failing_tests) == 1


def test_run_test_suite_on_current_repo():
    root = str(Path(__file__).resolve().parent.parent.parent)
    result = run_test_suite(root, custom_command="python -m pytest backend/tests/test_prompts.py", timeout=15)
    assert result.is_success is True
    assert result.passed >= 4
    assert result.failed == 0
