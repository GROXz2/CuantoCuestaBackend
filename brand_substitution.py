"""Utilities for brand substitution suggestions."""
from typing import Dict, List


def suggest_substitutions(
    brand: str,
    mapping: Dict[str, List[str]],
) -> List[str]:
    """Return alternative brands for a given brand.

    Args:
        brand: Brand name to substitute.
        mapping: Dictionary mapping brand names to alternative brand lists.
    Returns:
        List of alternative brands or empty list if none available.
    """
    return mapping.get(brand, [])
