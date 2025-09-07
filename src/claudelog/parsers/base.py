"""Base parser class for Claude log entries."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseParser(ABC):
    """Abstract base class for Claude log parsers."""
    
    # Version range this parser handles (inclusive)
    MIN_VERSION = None
    MAX_VERSION = None
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    @classmethod
    def can_handle(cls, version: str) -> bool:
        """Check if this parser can handle the given version.
        
        Args:
            version: Version string like "1.0.70"
            
        Returns:
            True if this parser can handle the version
        """
        if not version:
            return False
            
        try:
            # Parse version components
            parts = version.split('.')
            if len(parts) != 3:
                return False
                
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            current = (major, minor, patch)
            
            # Check against version range
            if cls.MIN_VERSION:
                min_parts = cls.MIN_VERSION.split('.')
                min_ver = (int(min_parts[0]), int(min_parts[1]), int(min_parts[2]))
                if current < min_ver:
                    return False
                    
            if cls.MAX_VERSION:
                max_parts = cls.MAX_VERSION.split('.')
                max_ver = (int(max_parts[0]), int(max_parts[1]), int(max_parts[2]))
                if current > max_ver:
                    return False
                    
            return True
        except (ValueError, IndexError):
            return False
    
    def parse_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a log entry and normalize its structure.
        
        Args:
            entry: Raw log entry from JSONL
            
        Returns:
            Normalized entry with consistent structure
        """
        # Handle special entry types that don't have standard structure
        entry_type = entry.get('type', 'unknown')
        
        if entry_type == 'summary':
            return self._parse_summary(entry)
        
        # Parse standard message entries
        return self._parse_message(entry)
    
    def _parse_summary(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a summary entry.
        
        Summary entries have minimal structure and no version/message fields.
        """
        return {
            'type': 'summary',
            'summary': entry.get('summary', ''),
            'leafUuid': entry.get('leafUuid'),
            'timestamp': None,
            'version': None,
            'message': None
        }
    
    @abstractmethod
    def _parse_message(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a message entry.
        
        Subclasses must implement this to handle version-specific formats.
        """
        pass
    
    def extract_content(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract text content from a message.
        
        Args:
            message: Message object from entry
            
        Returns:
            Extracted text or None
        """
        if not message:
            return None
            
        content = message.get('content')
        return self._extract_text_from_content(content)
    
    def _extract_text_from_content(self, content: Any) -> Optional[str]:
        """Extract text from various content formats.
        
        Handles both string and array formats.
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', item.get('content', '')))
                    elif 'text' in item:
                        text_parts.append(item['text'])
                elif isinstance(item, str):
                    text_parts.append(item)
            return '\n'.join(text_parts) if text_parts else None
        elif isinstance(content, dict):
            if 'text' in content:
                return content['text']
            elif 'content' in content:
                return self._extract_text_from_content(content['content'])
        return None
    
    def extract_tool_uses(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool use information from a message.
        
        Args:
            message: Message object from entry
            
        Returns:
            List of tool use dictionaries
        """
        if not message:
            return []
            
        tool_uses = []
        content = message.get('content')
        
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'tool_use':
                    tool_uses.append({
                        'name': item.get('name', 'Unknown'),
                        'id': item.get('id'),
                        'input': item.get('input', {})
                    })
        
        return tool_uses
    
    def extract_tool_result(self, entry: Dict[str, Any]) -> Optional[Any]:
        """Extract tool result from an entry.
        
        Args:
            entry: Log entry
            
        Returns:
            Tool result or None
        """
        # Handle both toolUseResult and tool_result fields
        return entry.get('toolUseResult') or entry.get('tool_result')