"""Adaptive parser that handles any Claude log format version."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..constants import MAX_RECURSION_DEPTH
from ..utils import load_json_config


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
            default_path = Path(__file__).parent.parent / "field_mappings.json"
            if default_path.exists():
                config_path = str(default_path)

        if config_path:
            config_file = Path(config_path) if not isinstance(config_path, Path) else config_path
            config = load_json_config(config_file)
            if config:
                self.field_aliases = config.get("field_aliases", {})
                return

        # Simplified field configuration - only actual field names used in Claude logs
        self.field_aliases = {
            "timestamp": ["timestamp"],
            "version": ["version"],
            "uuid": ["uuid"],
            "session_id": ["sessionId"],
            "request_id": ["requestId"],
            "parent_uuid": ["parentUuid"],
            "is_meta": ["isMeta"],
            "is_sidechain": ["isSidechain"],
            "tool_result": ["toolUseResult"],
            "working_dir": ["cwd"],
            "git_branch": ["gitBranch"],
            "user_type": ["userType"],
            "level": ["level"],
        }

    def parse_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse any log entry by discovering its structure.

        This method doesn't assume any specific format - it discovers
        what's available and normalizes it.
        """
        if not isinstance(entry, dict):
            return {"_raw": entry, "_parse_error": "Not a dictionary"}

        # Special handling for known minimal entries
        entry_type = self._find_field(entry, ["type", "entryType", "kind"])

        if entry_type == "summary":
            # Summary entries are minimal - just pass through
            return entry

        # Build normalized entry by discovering fields
        normalized = {
            "_raw": entry,  # Always keep original for debugging
        }

        # Discover and normalize common fields using config
        normalized["type"] = entry_type
        timestamp_fields = self.field_aliases.get("timestamp", ["timestamp"])
        normalized["timestamp"] = self._find_field(entry, timestamp_fields)
        version_fields = self.field_aliases.get("version", ["version"])
        normalized["version"] = self._find_field(entry, version_fields)

        # IDs and references
        uuid_fields = self.field_aliases.get("uuid", ["uuid", "id"])
        normalized["uuid"] = self._find_field(entry, uuid_fields)
        session_fields = self.field_aliases.get("session_id", ["sessionId"])
        normalized["sessionId"] = self._find_field(entry, session_fields)
        request_fields = self.field_aliases.get("request_id", ["requestId"])
        normalized["requestId"] = self._find_field(entry, request_fields)
        parent_fields = self.field_aliases.get("parent_uuid", ["parentUuid"])
        normalized["parentUuid"] = self._find_field(entry, parent_fields)

        # Message content - the most variable part
        normalized["message"] = self._extract_message(entry)

        # Metadata fields
        meta_fields = self.field_aliases.get("is_meta", ["isMeta"])
        normalized["isMeta"] = self._find_field(entry, meta_fields)
        sidechain_fields = self.field_aliases.get("is_sidechain", ["isSidechain"])
        normalized["isSidechain"] = self._find_field(entry, sidechain_fields)

        # Tool-related fields
        tool_fields = self.field_aliases.get("tool_result", ["toolUseResult"])
        normalized["toolUseResult"] = self._find_field(entry, tool_fields)

        # Working directory and git info
        cwd_fields = self.field_aliases.get("working_dir", ["cwd"])
        normalized["cwd"] = self._find_field(entry, cwd_fields)
        git_fields = self.field_aliases.get("git_branch", ["gitBranch"])
        normalized["gitBranch"] = self._find_field(entry, git_fields)

        # User type and level
        user_fields = self.field_aliases.get("user_type", ["userType"])
        normalized["userType"] = self._find_field(entry, user_fields)
        normalized["level"] = self._find_field(entry, self.field_aliases.get("level", ["level"]))

        # Keep any unknown fields as-is (for future compatibility)
        for key, value in entry.items():
            if key not in normalized and not key.startswith("_"):
                normalized[f"_unknown_{key}"] = value

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
        message = self._find_field(entry, ["message", "msg", "data", "payload"])

        if not message:
            # Maybe the entry itself is the message
            if "content" in entry or "text" in entry:
                message = entry

        if not message:
            return None

        # Normalize message structure
        if isinstance(message, str):
            return {"role": self._guess_role(entry), "content": message}
        elif isinstance(message, dict):
            return self._normalize_message_dict(message)
        elif isinstance(message, list):
            # Some formats might have message as array
            return {"role": self._guess_role(entry), "content": message}

        return None

    def _normalize_message_dict(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a message dictionary."""
        normalized = {}

        # Extract role
        role_fields = self.field_aliases.get("role", ["role"])
        normalized["role"] = self._find_field(message, role_fields) or "unknown"

        # Extract content - most variable part
        content = self._find_field(message, self.field_aliases.get("content", ["content"]))
        normalized["content"] = content

        # Preserve other fields
        for key in ["id", "model", "usage", "stop_reason"]:
            if key in message:
                normalized[key] = message[key]

        return normalized

    def _guess_role(self, entry: Dict[str, Any]) -> str:
        """Guess the role from entry type or other fields."""
        entry_type = self._find_field(entry, ["type", "entryType"])
        if entry_type in ["user", "human", "input"]:
            return "user"
        elif entry_type in ["assistant", "ai", "claude", "output"]:
            return "assistant"
        elif entry_type in ["system", "info", "meta"]:
            return "system"
        return "unknown"

    def extract_content_text(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract readable text from any entry format."""
        message = entry.get("message")
        if not message:
            return None

        content = message.get("content") if isinstance(message, dict) else None
        if not content:
            return None

        return self._extract_text_from_content(content)

    def _extract_text_from_content(self, content: Any, depth: int = 0) -> Optional[str]:
        """Extract text from various content formats.

        Args:
            content: Content to extract text from
            depth: Current recursion depth (for preventing stack overflow)
        """
        # Prevent excessive recursion
        if depth > MAX_RECURSION_DEPTH:
            return "[Content too deeply nested]"

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
                    for field in ["text", "content", "value", "data"]:
                        if field in item:
                            text = self._extract_text_from_content(item[field], depth + 1)
                            if text:
                                break

                    # Special handling for type=text
                    if not text and item.get("type") == "text":
                        text = self._extract_text_from_content(item, depth + 1)

                    if text:
                        texts.append(text)
                elif isinstance(item, str):
                    texts.append(item)
                else:
                    # Try converting to string
                    texts.append(str(item))

            return "\n".join(texts) if texts else None

        if isinstance(content, dict):
            # Try common text fields
            for field in ["text", "content", "value", "body", "message"]:
                if field in content:
                    text = self._extract_text_from_content(content[field], depth + 1)
                    if text:
                        return text

            # Special case: type=text with content/text field
            if content.get("type") == "text":
                for field in ["text", "content"]:
                    if field in content:
                        return self._extract_text_from_content(content[field], depth + 1)

        # Last resort - convert to string
        try:
            return json.dumps(content) if isinstance(content, (dict, list)) else str(content)
        except (TypeError, ValueError, RecursionError, OverflowError):
            # Only catch specific exceptions that could occur during serialization
            return None

    def extract_tool_info(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tool-related information from any format."""
        result = {"tool_uses": [], "tool_result": None}

        message = entry.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type == "tool_use":
                            result["tool_uses"].append(
                                {
                                    "name": item.get("name"),
                                    "id": item.get("id"),
                                    "input": item.get("input"),
                                }
                            )

        # Look for tool results
        tool_result_fields = self.field_aliases.get("tool_result", ["toolUseResult"])
        result["tool_result"] = self._find_field(entry, tool_result_fields)

        return result
