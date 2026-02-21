"""
Utility helpers used across the simulation modules.
"""

import math


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))


def shannon_entropy(p: float) -> float:
    """
    Binary Shannon entropy H(p) = -p*log2(p) - (1-p)*log2(1-p).
    Returns 0 when p is 0 or 1 (no uncertainty), 1 when p=0.5 (maximum).
    """
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns *default* when denominator is zero."""
    return numerator / denominator if denominator != 0 else default
