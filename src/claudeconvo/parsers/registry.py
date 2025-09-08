"""
Registry for parsers - simplified to use AdaptiveParser for all versions.

This module provides a unified interface for obtaining parsers. Currently
it always returns the AdaptiveParser since it handles all Claude log format
versions automatically.

Example usage:
    parser = get_parser()
    parsed = parser.parse_entry(entry)
"""

from typing import Any, Dict, Optional

from .adaptive import AdaptiveParser

################################################################################

def get_parser(
    version : Optional[str]           = None,
    entry   : Optional[Dict[str, Any]] = None
) -> AdaptiveParser:
    """
    Get a parser instance.

    The AdaptiveParser handles all versions automatically, so we always return it.

    Args:
        version: Version string (ignored - kept for compatibility)
        entry: Log entry (used for validation only)

    Returns:
        AdaptiveParser instance that can handle any Claude log format version
    """
    # Validate entry parameter if provided (for test compatibility)
    if entry is not None and not isinstance(entry, dict):
        raise TypeError(f"Entry must be a dictionary, got {type(entry).__name__}")

    # Always return AdaptiveParser - it handles all versions
    return AdaptiveParser()
