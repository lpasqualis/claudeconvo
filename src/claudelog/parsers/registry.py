"""Registry for version-specific parsers."""

import sys
from typing import Any, Dict, Optional
from .base import BaseParser
from .v1_0_70 import ParserV1_0_70
from .v1_0_80 import ParserV1_0_80


# Registry of available parsers
PARSERS = [
    ParserV1_0_70,
    ParserV1_0_80,
]


def detect_version(entry: Dict[str, Any]) -> Optional[str]:
    """Detect the version from a log entry.
    
    Args:
        entry: Log entry dictionary
        
    Returns:
        Version string or None if not found
    """
    # Direct version field
    if 'version' in entry:
        return entry['version']
    
    # Check in message field (some formats nest it)
    message = entry.get('message', {})
    if isinstance(message, dict) and 'version' in message:
        return message['version']
    
    return None


def get_parser(version: Optional[str] = None, entry: Optional[Dict[str, Any]] = None) -> BaseParser:
    """Get the appropriate parser for a version or entry.
    
    Args:
        version: Version string (optional)
        entry: Log entry to detect version from (optional)
        
    Returns:
        Appropriate parser instance
    """
    # Try to detect version from entry if not provided
    if not version and entry:
        version = detect_version(entry)
    
    # Find matching parser
    if version:
        for parser_class in PARSERS:
            if parser_class.can_handle(version):
                return parser_class()
    
    # Fallback to latest parser for unknown versions
    # This ensures forward compatibility
    print(f"Warning: Unknown version '{version}', using latest parser", file=sys.stderr)
    return ParserV1_0_80()


class UnifiedParser:
    """Unified parser that automatically selects the right version parser."""
    
    def __init__(self):
        """Initialize the unified parser."""
        self._parser_cache = {}
    
    def parse_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse an entry using the appropriate version parser.
        
        Args:
            entry: Raw log entry
            
        Returns:
            Normalized entry
        """
        # Detect version
        version = detect_version(entry)
        
        # Get cached parser or create new one
        if version not in self._parser_cache:
            self._parser_cache[version] = get_parser(version, entry)
        
        parser = self._parser_cache[version]
        
        try:
            return parser.parse_entry(entry)
        except Exception as e:
            # Graceful fallback - return original entry with error flag
            print(f"Warning: Failed to parse entry: {e}", file=sys.stderr)
            entry['_parse_error'] = str(e)
            return entry
    
    def extract_content(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract content from a message using appropriate parser.
        
        Args:
            message: Message dictionary
            
        Returns:
            Extracted text or None
        """
        # Use latest parser for content extraction (should be version-agnostic)
        parser = ParserV1_0_80()
        return parser.extract_content(message)
    
    def extract_tool_uses(self, message: Dict[str, Any]) -> list:
        """Extract tool uses from a message.
        
        Args:
            message: Message dictionary
            
        Returns:
            List of tool use dictionaries
        """
        parser = ParserV1_0_80()
        return parser.extract_tool_uses(message)
    
    def extract_tool_result(self, entry: Dict[str, Any]) -> Optional[Any]:
        """Extract tool result from an entry.
        
        Args:
            entry: Log entry
            
        Returns:
            Tool result or None
        """
        parser = ParserV1_0_80()
        return parser.extract_tool_result(entry)