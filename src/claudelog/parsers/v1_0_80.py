"""Parser for Claude log format v1.0.80 and later."""

from typing import Any, Dict

from .base import BaseParser


class ParserV1080(BaseParser):
    """Parser for Claude log format versions 1.0.80 and later."""

    MIN_VERSION = "1.0.80"
    MAX_VERSION = None  # Open-ended for future versions

    def _parse_message(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a message entry for v1.0.80+ format.

        In these versions:
        - Content structure may have changed
        - New fields might be present
        - Cache-related fields in usage
        """
        # Use base implementation
        parsed = super()._parse_message(entry)

        # Handle any new fields gracefully
        for key in entry:
            if key not in parsed:
                parsed[key] = entry[key]

        return parsed

    def _normalize_message(self, message: Any) -> Dict[str, Any]:
        """Normalize message structure for v1.0.80+.

        Handles expanded usage fields with cache information.
        """
        if not message:
            return {}

        if isinstance(message, str):
            return {"role": "unknown", "content": message}
        elif isinstance(message, dict):
            normalized = {
                "role": message.get("role", "unknown"),
                "content": message.get("content"),
                "id": message.get("id"),
                "model": message.get("model"),
                "stop_reason": message.get("stop_reason"),
                "stop_sequence": message.get("stop_sequence"),
            }

            # Handle expanded usage structure with cache fields
            if "usage" in message:
                usage = message["usage"]
                if isinstance(usage, dict):
                    normalized["usage"] = {
                        "input_tokens": usage.get("input_tokens"),
                        "output_tokens": usage.get("output_tokens"),
                        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
                        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
                        "cache_creation": usage.get("cache_creation"),
                        "service_tier": usage.get("service_tier"),
                    }
                else:
                    normalized["usage"] = usage

            return normalized
        else:
            return {}
