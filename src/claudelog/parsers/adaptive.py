"""Adaptive parser that handles any Claude log format version."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class AdaptiveParser:
    """Self-adapting parser that handles any log format through field discovery."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the adaptive parser.
        
        Args:
            config_path: Path to field mappings config file. If None, uses defaults.
        """
        self._field_cache = {}
        self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None):
        """Load field mapping configuration."""
        # Try to load from file
        if not config_path:
            # Look for config in package directory
            default_path = Path(__file__).parent.parent / 'field_mappings.json'
            if default_path.exists():
                config_path = str(default_path)
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    self.field_aliases = config.get('field_aliases', {})
                    self.tool_patterns = config.get('tool_patterns', {})
                    self.special_entries = config.get('special_entries', {})
                    return
            except Exception:
                pass  # Fall back to defaults
        
        # Default configuration if file not found
        self.field_aliases = {
            'content': ['content', 'text', 'message', 'body', 'data'],
            'role': ['role', 'type', 'sender', 'author'],
            'timestamp': ['timestamp', 'time', 'created', 'createdAt', 'datetime'],
            'version': ['version', 'ver', 'v'],
            'tool_result': ['toolUseResult', 'tool_result', 'toolResult', 'result', 'output']
        }
        self.tool_patterns = {
            'tool_use_types': ['tool_use', 'tool', 'function_call'],
            'tool_name_fields': ['name', 'tool', 'function'],
            'tool_id_fields': ['id', 'tool_id', 'call_id'],
            'tool_input_fields': ['input', 'arguments', 'params', 'data']
        }
        self.special_entries = {
            'summary': {'minimal_fields': ['type', 'summary', 'leafUuid'], 'skip_normalization': True}
        }
    
    def parse_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse any log entry by discovering its structure.
        
        This method doesn't assume any specific format - it discovers
        what's available and normalizes it.
        """
        if not isinstance(entry, dict):
            return {'_raw': entry, '_parse_error': 'Not a dictionary'}
        
        # Special handling for known minimal entries
        entry_type = self._find_field(entry, ['type', 'entryType', 'kind'])
        
        if entry_type == 'summary':
            # Summary entries are minimal - just pass through
            return entry
        
        # Build normalized entry by discovering fields
        normalized = {
            '_raw': entry,  # Always keep original for debugging
        }
        
        # Discover and normalize common fields using config
        normalized['type'] = entry_type
        normalized['timestamp'] = self._find_field(entry, self.field_aliases.get('timestamp', ['timestamp']))
        normalized['version'] = self._find_field(entry, self.field_aliases.get('version', ['version']))
        
        # IDs and references
        normalized['uuid'] = self._find_field(entry, self.field_aliases.get('uuid', ['uuid', 'id']))
        normalized['sessionId'] = self._find_field(entry, self.field_aliases.get('session_id', ['sessionId']))
        normalized['requestId'] = self._find_field(entry, self.field_aliases.get('request_id', ['requestId']))
        normalized['parentUuid'] = self._find_field(entry, self.field_aliases.get('parent_uuid', ['parentUuid']))
        
        # Message content - the most variable part
        normalized['message'] = self._extract_message(entry)
        
        # Metadata fields
        normalized['isMeta'] = self._find_field(entry, self.field_aliases.get('is_meta', ['isMeta']))
        normalized['isSidechain'] = self._find_field(entry, self.field_aliases.get('is_sidechain', ['isSidechain']))
        
        # Tool-related fields
        normalized['toolUseResult'] = self._find_field(entry, self.field_aliases.get('tool_result', ['toolUseResult']))
        
        # Working directory and git info
        normalized['cwd'] = self._find_field(entry, self.field_aliases.get('working_dir', ['cwd']))
        normalized['gitBranch'] = self._find_field(entry, self.field_aliases.get('git_branch', ['gitBranch']))
        
        # User type and level
        normalized['userType'] = self._find_field(entry, self.field_aliases.get('user_type', ['userType']))
        normalized['level'] = self._find_field(entry, self.field_aliases.get('level', ['level']))
        
        # Keep any unknown fields as-is (for future compatibility)
        for key, value in entry.items():
            if key not in normalized and not key.startswith('_'):
                normalized[f'_unknown_{key}'] = value
        
        return normalized
    
    def _find_field(self, obj: Dict[str, Any], candidates: List[str]) -> Optional[Any]:
        """Find the first matching field from a list of candidates.
        
        This allows us to handle field renames across versions.
        """
        for field in candidates:
            if field in obj:
                return obj[field]
        return None
    
    def _extract_message(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and normalize message content from various formats."""
        # Look for message in common locations
        message = self._find_field(entry, ['message', 'msg', 'data', 'payload'])
        
        if not message:
            # Maybe the entry itself is the message
            if 'content' in entry or 'text' in entry:
                message = entry
        
        if not message:
            return None
        
        # Normalize message structure
        if isinstance(message, str):
            return {
                'role': self._guess_role(entry),
                'content': message
            }
        elif isinstance(message, dict):
            return self._normalize_message_dict(message)
        elif isinstance(message, list):
            # Some formats might have message as array
            return {
                'role': self._guess_role(entry),
                'content': message
            }
        
        return None
    
    def _normalize_message_dict(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a message dictionary."""
        normalized = {}
        
        # Extract role
        normalized['role'] = self._find_field(message, self.field_aliases.get('role', ['role'])) or 'unknown'
        
        # Extract content - most variable part
        content = self._find_field(message, self.field_aliases.get('content', ['content']))
        normalized['content'] = content
        
        # Preserve other fields
        for key in ['id', 'model', 'usage', 'stop_reason']:
            if key in message:
                normalized[key] = message[key]
        
        return normalized
    
    def _guess_role(self, entry: Dict[str, Any]) -> str:
        """Guess the role from entry type or other fields."""
        entry_type = self._find_field(entry, ['type', 'entryType'])
        if entry_type in ['user', 'human', 'input']:
            return 'user'
        elif entry_type in ['assistant', 'ai', 'claude', 'output']:
            return 'assistant'
        elif entry_type in ['system', 'info', 'meta']:
            return 'system'
        return 'unknown'
    
    def extract_content_text(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract readable text from any entry format."""
        message = entry.get('message')
        if not message:
            return None
        
        content = message.get('content') if isinstance(message, dict) else None
        if not content:
            return None
        
        return self._extract_text_from_content(content)
    
    def _extract_text_from_content(self, content: Any) -> Optional[str]:
        """Recursively extract text from various content formats."""
        if content is None:
            return None
        
        if isinstance(content, str):
            return content
        
        if isinstance(content, (int, float, bool)):
            return str(content)
        
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict):
                    # Look for text in common fields
                    text = None
                    for field in ['text', 'content', 'value', 'data']:
                        if field in item:
                            text = self._extract_text_from_content(item[field])
                            if text:
                                break
                    
                    # Special handling for tool_use type
                    if not text and item.get('type') == 'text':
                        text = self._extract_text_from_content(item)
                    
                    if text:
                        texts.append(text)
                elif isinstance(item, str):
                    texts.append(item)
                else:
                    # Try converting to string
                    texts.append(str(item))
            
            return '\n'.join(texts) if texts else None
        
        if isinstance(content, dict):
            # Try common text fields
            for field in ['text', 'content', 'value', 'body', 'message']:
                if field in content:
                    text = self._extract_text_from_content(content[field])
                    if text:
                        return text
            
            # Special case: type=text with content/text field
            if content.get('type') == 'text':
                for field in ['text', 'content']:
                    if field in content:
                        return self._extract_text_from_content(content[field])
        
        # Last resort - convert to string
        try:
            return json.dumps(content) if isinstance(content, (dict, list)) else str(content)
        except:
            return None
    
    def extract_tool_info(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tool-related information from any format."""
        result = {
            'tool_uses': [],
            'tool_result': None
        }
        
        message = entry.get('message')
        if isinstance(message, dict):
            content = message.get('content')
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get('type')
                        if item_type in self.tool_patterns.get('tool_use_types', ['tool_use']):
                            result['tool_uses'].append({
                                'name': self._find_field(item, self.tool_patterns.get('tool_name_fields', ['name'])),
                                'id': self._find_field(item, self.tool_patterns.get('tool_id_fields', ['id'])),
                                'input': self._find_field(item, self.tool_patterns.get('tool_input_fields', ['input']))
                            })
        
        # Look for tool results
        result['tool_result'] = self._find_field(entry, self.field_aliases.get('tool_result', ['toolUseResult']))
        
        return result