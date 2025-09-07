"""Base parser class for Claude log entries."""

import json
from abc import ABC
from typing import Any, Dict, Optional

from ..constants import MAX_RECURSION_DEPTH


class BaseParser(ABC):
    """Abstract base class for Claude log parsers."""

    # Version range this parser handles (inclusive)
    MIN_VERSION = None
    MAX_VERSION = None

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
            parts = version.split(".")
            if len(parts) != 3:
                return False

            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            current = (major, minor, patch)

            # Check against version range
            if cls.MIN_VERSION:
                min_parts = cls.MIN_VERSION.split(".")
                min_ver = (int(min_parts[0]), int(min_parts[1]), int(min_parts[2]))
                if current < min_ver:
                    return False

            if cls.MAX_VERSION:
                max_parts = cls.MAX_VERSION.split(".")
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
        entry_type = entry.get("type", "unknown")

        if entry_type == "summary":
            return self._parse_summary(entry)

        # Parse standard message entries
        return self._parse_message(entry)

    def _parse_summary(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a summary entry.

        Summary entries have minimal structure and no version/message fields.
        """
        return {
            "type": "summary",
            "summary": entry.get("summary", ""),
            "leafUuid": entry.get("leafUuid"),
            "timestamp": None,
            "version": None,
            "message": None,
        }

    def _parse_message(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a message entry with common field normalization.

        Subclasses can override to handle version-specific formats.
        """
        return {
            "type": entry.get("type"),
            "timestamp": entry.get("timestamp"),
            "version": entry.get("version"),
            "sessionId": entry.get("sessionId"),
            "uuid": entry.get("uuid"),
            "parentUuid": entry.get("parentUuid"),
            "isSidechain": entry.get("isSidechain", False),
            "isMeta": entry.get("isMeta", False),
            "userType": entry.get("userType"),
            "cwd": entry.get("cwd"),
            "gitBranch": entry.get("gitBranch"),
            "level": entry.get("level"),
            "requestId": entry.get("requestId"),
            "message": self._normalize_message(entry.get("message")),
            "toolUseResult": entry.get("toolUseResult"),
        }

    def _normalize_message(self, message: Any) -> Dict[str, Any]:
        """Normalize message structure.

        Ensures consistent structure regardless of input format.
        Subclasses can override for version-specific handling.
        """
        if not message:
            return {}

        if isinstance(message, str):
            # Handle string messages (defensive)
            return {"role": "unknown", "content": message}
        elif isinstance(message, dict):
            # Standard message structure
            return {
                "role": message.get("role", "unknown"),
                "content": message.get("content"),
                "id": message.get("id"),
                "model": message.get("model"),
                "usage": message.get("usage"),
                "stop_reason": message.get("stop_reason"),
                "stop_sequence": message.get("stop_sequence"),
            }
        else:
            return {}

    def extract_content(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract text content from a message.

        Args:
            message: Message object from entry

        Returns:
            Extracted text or None
        """
        if not message:
            return None

        content = message.get("content")
        return self._extract_text_from_content(content)

    def _extract_text_from_content(self, content: Any, depth: int = 0) -> Optional[str]:
        """Recursively extract text from various content formats.

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
