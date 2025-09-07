"""Parser for Claude log format v1.0.70 through v1.0.79."""

from .base import BaseParser


class ParserV1070(BaseParser):
    """Parser for Claude log format versions 1.0.70-1.0.79."""

    MIN_VERSION = "1.0.70"
    MAX_VERSION = "1.0.79"

    # Uses default _parse_message and _normalize_message from BaseParser
    # No version-specific handling needed for v1.0.70-1.0.79
