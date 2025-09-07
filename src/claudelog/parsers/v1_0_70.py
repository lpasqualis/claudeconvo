"""Parser for Claude log format v1.0.70 through v1.0.79."""

from typing import Any, Dict
from .base import BaseParser


class ParserV1_0_70(BaseParser):
    """Parser for Claude log format versions 1.0.70-1.0.79."""
    
    MIN_VERSION = "1.0.70"
    MAX_VERSION = "1.0.79"
    
    def _parse_message(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a message entry for v1.0.70-1.0.79 format.
        
        In these versions:
        - User messages have content as a string
        - Assistant messages have content as an array
        - Tool results are in 'toolUseResult' field
        """
        return {
            'type': entry.get('type'),
            'timestamp': entry.get('timestamp'),
            'version': entry.get('version'),
            'sessionId': entry.get('sessionId'),
            'uuid': entry.get('uuid'),
            'parentUuid': entry.get('parentUuid'),
            'isSidechain': entry.get('isSidechain', False),
            'isMeta': entry.get('isMeta', False),
            'userType': entry.get('userType'),
            'cwd': entry.get('cwd'),
            'gitBranch': entry.get('gitBranch'),
            'level': entry.get('level'),
            'requestId': entry.get('requestId'),
            'message': self._normalize_message(entry.get('message')),
            'toolUseResult': entry.get('toolUseResult')
        }
    
    def _normalize_message(self, message: Any) -> Dict[str, Any]:
        """Normalize message structure.
        
        Ensures consistent structure regardless of input format.
        """
        if not message:
            return {}
            
        if isinstance(message, str):
            # Handle string messages (shouldn't happen but be defensive)
            return {
                'role': 'unknown',
                'content': message
            }
        elif isinstance(message, dict):
            # Standard message structure
            return {
                'role': message.get('role', 'unknown'),
                'content': message.get('content'),
                'id': message.get('id'),
                'model': message.get('model'),
                'usage': message.get('usage'),
                'stop_reason': message.get('stop_reason')
            }
        else:
            return {}