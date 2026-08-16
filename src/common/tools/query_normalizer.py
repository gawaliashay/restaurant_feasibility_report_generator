# src\common\tools\clients\query_normalizer.py
"""
Query normalization utilities.
"""

from typing import Tuple, Optional


def normalize_query(query: str | list[str]) -> Tuple[str, Optional[str]]:
    """
    Convert query to string and validate it.
    
    Args:
        query: String or list of strings
        
    Returns:
        Tuple of (normalized_query, error_message)
        If valid, error_message is None.
    """
    # Handle list input - take first item
    if isinstance(query, list):
        if not query:
            return "", "Query list cannot be empty"
        query = query[0]
    
    # Validate string
    if not query or len(query.strip()) < 3:
        return "", "Query must be at least 3 characters"
    
    return query.strip(), None