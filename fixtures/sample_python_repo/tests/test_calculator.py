"""
Tests for sample calculator module.
"""
import pytest
from app.calculator import add, subtract, divide

def test_add():
    assert add(2, 3) == 5

def test_subtract():
    # Will fail initially due to intentional bug in calculator.py
    assert subtract(10, 4) == 6

def test_divide():
    assert divide(10, 2) == 5.0
    with pytest.raises(ValueError):
        divide(5, 0)
