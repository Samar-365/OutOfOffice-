"""
Sample calculator module with an intentional logic bug for AI testing.
"""

def add(a: int, b: int) -> int:
    return a + b

def subtract(a: int, b: int) -> int:
    # BUG: plus instead of minus
    return a + b

def divide(a: int, b: int) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
